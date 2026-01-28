"""보이스오버 에이전트 - Qwen3-TTS로 대본 음성 생성"""
from agents.config import agent_settings

import sys
import os
import json
import base64
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum

sys.path.append("/app")

from agents.base import BaseAgent, AgentResult, AgentStatus


def emit_progress(status: str, detail: str = ""):
    """진행 상황 발생"""
    try:
        import builtins
        if hasattr(builtins, "emit_agent_progress"):
            builtins.emit_agent_progress(status, detail)
    except:
        pass


class VoicePhase(Enum):
    ASK_OPTION = "ask_option"
    ASK_CLONE_TYPE = "ask_clone_type"  # YouTube or Sample
    ASK_YOUTUBE_INFO = "ask_youtube_info"
    ASK_SAMPLE_SELECT = "ask_sample_select"
    GENERATING = "generating"
    CONFIRM = "confirm"


class VoiceoverAgent(BaseAgent):
    """Qwen3-TTS 보이스오버 에이전트"""
    
    TTS_CUSTOM_URL = agent_settings.tts_custom_url  # CustomVoice (프리셋)
    TTS_BASE_URL = agent_settings.tts_base_url    # Base (클로닝)
    DEFAULT_SPEAKER = "Sohee"
    DEFAULT_LANGUAGE = "Korean"
    OUTPUT_DIR = Path("/app/output/voiceover")
    SAMPLES_DIR = Path("/data/dbs/routine/youtube-studio/voices/samples_cut")
    SAMPLES_JSON = Path("/data/dbs/routine/youtube-studio/voices/samples_cut_prompts.json")
    
    def __init__(self):
        super().__init__("VoiceoverAgent")
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.phase = VoicePhase.ASK_OPTION
        self.voice_option = None  # "default", "youtube", "sample"
        self.youtube_url = None
        self.youtube_time = None
        self.sample_file = None
        self.sample_text = None
        self.samples_list = []
    
    def _load_samples(self) -> List[Dict]:
        """저장된 샘플 목록 로드"""
        if self.SAMPLES_JSON.exists():
            with open(self.SAMPLES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("prompts", [])[:20]  # 최대 20개
        return []
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """보이스오버 시작 - 옵션 선택"""
        self.status = AgentStatus.RUNNING
        self.phase = VoicePhase.ASK_OPTION
        
        # context 저장
        self.context = input_data
        
        script = input_data.get("script", {})
        if not script:
            return AgentResult(
                success=False,
                step="voiceover",
                message="대본이 없습니다. 먼저 대본을 작성해주세요.",
                needs_feedback=False
            )
        
        message = """AI 보이스오버를 생성할 준비가 되었습니다!

**음성 옵션을 선택해주세요:**

**1. 기본 보이스 (Sohee)**
   한국어에 최적화된 따뜻한 여성 음성
   바로 생성 가능

**2. 보이스 클로닝**
   원하는 목소리로 복제하여 생성
   (YouTube 영상 또는 저장된 샘플 사용)

번호를 입력해주세요. (1 또는 2)"""
        
        self.status = AgentStatus.WAITING_FEEDBACK
        
        return AgentResult(
            success=True,
            step="voiceover_option",
            message=message,
            needs_feedback=True,
            data={"phase": self.phase.value, "options": ["기본 보이스", "보이스 클로닝"]}
        )
    
    async def handle_feedback(self, feedback: str, images: List[str] = None) -> AgentResult:
        """피드백 처리 - 페이즈별 분기"""
        feedback_lower = feedback.lower().strip()
        
        # ========== 옵션 선택 단계 ==========
        if self.phase == VoicePhase.ASK_OPTION:
            if any(kw in feedback for kw in ["1", "기본", "sohee", "소희", "default"]):
                self.voice_option = "default"
                self.phase = VoicePhase.GENERATING
                return AgentResult(
                    success=True,
                    step="voiceover_ready",
                    message="기본 보이스(Sohee)로 생성합니다.\n\n생성을 입력하면 보이스오버 생성을 시작합니다.",
                    needs_feedback=True,
                    data={"voice_option": "default", "speaker": "Sohee"}
                )
            
            elif any(kw in feedback for kw in ["2", "클로닝", "클론", "clone", "복제"]):
                self.phase = VoicePhase.ASK_CLONE_TYPE
                return AgentResult(
                    success=True,
                    step="voiceover_clone_type",
                    message="""보이스 클로닝 방식을 선택해주세요:

**1. YouTube 영상에서 추출**
   원하는 유튜브 영상의 URL과 해당 인물 음성이 나오는 시간대(최소 3초)를 입력

**2. 저장된 샘플 보이스 선택**
   미리 준비된 다양한 음성 샘플 중 선택

번호를 입력해주세요. (1 또는 2)""",
                    needs_feedback=True,
                    data={"phase": "ask_clone_type"}
                )
            
            return AgentResult(
                success=True,
                step="voiceover_option",
                message="1 (기본 보이스) 또는 2 (보이스 클로닝)를 입력해주세요.",
                needs_feedback=True
            )
        
        # ========== 클로닝 타입 선택 ==========
        if self.phase == VoicePhase.ASK_CLONE_TYPE:
            if any(kw in feedback for kw in ["1", "youtube", "유튜브", "영상"]):
                self.voice_option = "youtube"
                self.phase = VoicePhase.ASK_YOUTUBE_INFO
                return AgentResult(
                    success=True,
                    step="voiceover_youtube",
                    message="""YouTube 영상 정보를 입력해주세요.

다음 형식으로 입력:
**영상 URL, 시작시간-끝시간**

예시:
- https://youtube.com/watch?v=xxx, 1:30-1:45
- https://youtu.be/xxx, 0:05-0:15

(최소 3초 이상, 최대 30초의 깨끗한 음성 구간)""",
                    needs_feedback=True,
                    data={"voice_option": "youtube"}
                )
            
            elif any(kw in feedback for kw in ["2", "sample", "샘플", "저장"]):
                self.voice_option = "sample"
                self.samples_list = self._load_samples()
                self.phase = VoicePhase.ASK_SAMPLE_SELECT
                
                # 샘플 목록 표시 (최대 10개)
                sample_list = "\n".join([
                    f"**{i+1}.** {s.get(prompt_text, )[:40]}..."
                    for i, s in enumerate(self.samples_list[:10])
                ])
                
                return AgentResult(
                    success=True,
                    step="voiceover_sample",
                    message=f"""저장된 샘플 보이스 목록입니다:

{sample_list}

번호를 입력하여 선택해주세요. (1-{min(10, len(self.samples_list))})""",
                    needs_feedback=True,
                    data={"voice_option": "sample", "samples_count": len(self.samples_list)}
                )
            
            return AgentResult(
                success=True,
                step="voiceover_clone_type",
                message="1 (YouTube) 또는 2 (저장된 샘플)를 입력해주세요.",
                needs_feedback=True
            )
        
        # ========== YouTube 정보 입력 ==========
        if self.phase == VoicePhase.ASK_YOUTUBE_INFO:
            # URL과 시간 파싱
            import re
            
            # URL 추출
            url_match = re.search(r"(https?://[^\s,]+)", feedback)
            if url_match:
                self.youtube_url = url_match.group(1)
            
            # 시간 추출 (MM:SS-MM:SS 또는 M:SS-M:SS)
            time_match = re.search(r"(\d+:\d+)\s*[-~]\s*(\d+:\d+)", feedback)
            if time_match:
                self.youtube_time = (time_match.group(1), time_match.group(2))
            
            if self.youtube_url and self.youtube_time:
                self.phase = VoicePhase.GENERATING
                return AgentResult(
                    success=True,
                    step="voiceover_ready",
                    message=f"""YouTube 클로닝 정보 확인:
- URL: {self.youtube_url}
- 구간: {self.youtube_time[0]} ~ {self.youtube_time[1]}

생성을 입력하면 보이스오버 생성을 시작합니다.
(영상에서 음성 추출 후 클로닝합니다)""",
                    needs_feedback=True,
                    data={"voice_option": "youtube", "url": self.youtube_url, "time": self.youtube_time}
                )
            
            return AgentResult(
                success=True,
                step="voiceover_youtube",
                message="URL과 시간을 함께 입력해주세요.\n예: https://youtube.com/watch?v=xxx, 1:30-1:45",
                needs_feedback=True
            )
        
        # ========== 샘플 선택 ==========
        if self.phase == VoicePhase.ASK_SAMPLE_SELECT:
            try:
                idx = int(feedback.strip()) - 1
                if 0 <= idx < len(self.samples_list):
                    sample = self.samples_list[idx]
                    self.sample_file = sample.get("filename")
                    self.sample_text = sample.get("prompt_text", "")
                    self.phase = VoicePhase.GENERATING
                    
                    return AgentResult(
                        success=True,
                        step="voiceover_ready",
                        message=f"""샘플 보이스 선택 완료:
- 파일: {self.sample_file}
- 텍스트: {self.sample_text[:50]}...

생성을 입력하면 보이스오버 생성을 시작합니다.""",
                        needs_feedback=True,
                        data={"voice_option": "sample", "sample_file": self.sample_file}
                    )
            except ValueError:
                pass
            
            return AgentResult(
                success=True,
                step="voiceover_sample",
                message=f"1부터 {min(10, len(self.samples_list))} 사이의 번호를 입력해주세요.",
                needs_feedback=True
            )
        
        # ========== 생성 단계 ==========
        if self.phase == VoicePhase.GENERATING:
            if any(kw in feedback for kw in ["생성", "시작", "만들어", "go", "start"]):
                return await self._generate_voiceover()
            
            return AgentResult(
                success=True,
                step="voiceover_ready",
                message="생성을 입력하면 보이스오버 생성을 시작합니다.",
                needs_feedback=True
            )
        
        # ========== 확정 단계 ==========
        if self.phase == VoicePhase.CONFIRM:
            if any(kw in feedback for kw in ["확정", "좋아", "완료", "다음", "ok"]):
                self.status = AgentStatus.COMPLETED
                return AgentResult(
                    success=True,
                    step="voiceover_confirmed",
                    message="보이스오버가 확정되었습니다! 모든 작업이 완료되었습니다.",
                    needs_feedback=False
                )
            
            if any(kw in feedback for kw in ["다시", "재생성"]):
                return await self._generate_voiceover()
        
        return AgentResult(
            success=True,
            step="voiceover",
            message="확정을 입력하면 완료됩니다.",
            needs_feedback=True
        )
    
    async def _generate_voiceover(self) -> AgentResult:
        """보이스오버 실제 생성"""
        script = self.context.get("script", {})
        session_id = self.context.get("session_id", "unknown")
        
        sections = self._extract_sections(script)
        
        if not sections:
            return AgentResult(
                success=False,
                step="voiceover",
                message="대본에서 텍스트를 추출할 수 없습니다.",
                needs_feedback=True
            )
        
        # 클로닝용 ref 데이터 준비
        ref_audio_b64 = None
        ref_text = None
        
        if self.voice_option == "youtube" and self.youtube_url and self.youtube_time:
            emit_progress("보이스오버", "YouTube에서 음성 추출 중...")
            try:
                from agents.benchmarker.voice_service import voice_service
                audio_bytes, video_id = await voice_service.extract_audio_segment(
                    self.youtube_url,
                    self.youtube_time[0],
                    self.youtube_time[1]
                )
                ref_audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                
                # 자막 추출 시도
                ref_text = await voice_service.get_transcript_segment(
                    self.youtube_url,
                    self.youtube_time[0],
                    self.youtube_time[1]
                )
            except Exception as e:
                return AgentResult(
                    success=False,
                    step="voiceover",
                    message=f"YouTube 음성 추출 실패: {str(e)}",
                    needs_feedback=True
                )
        
        elif self.voice_option == "sample" and self.sample_file:
            emit_progress("보이스오버", "샘플 보이스 로드 중...")
            sample_path = self.SAMPLES_DIR / self.sample_file
            if sample_path.exists():
                with open(sample_path, "rb") as f:
                    ref_audio_b64 = base64.b64encode(f.read()).decode("utf-8")
                ref_text = self.sample_text
            else:
                return AgentResult(
                    success=False,
                    step="voiceover",
                    message=f"샘플 파일을 찾을 수 없습니다: {self.sample_file}",
                    needs_feedback=True
                )
        
        emit_progress("보이스오버 생성", f"총 {len(sections)}개 섹션 처리 시작...")
        
        results = []
        total = len(sections)
        
        for i, (section_name, text) in enumerate(sections):
            emit_progress("보이스오버 생성", f"[{i+1}/{total}] {section_name} 생성 중...")
            
            try:
                if self.voice_option in ["youtube", "sample"] and ref_audio_b64:
                    audio_data = await self._generate_clone(text, ref_audio_b64, ref_text)
                else:
                    audio_data = await self._generate_default(text)
                
                if audio_data:
                    filename = f"{session_id}_{i+1}_{section_name}.wav"
                    filepath = self.OUTPUT_DIR / filename
                    
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(audio_data))
                    
                    results.append({
                        "section": section_name,
                        "filename": filename,
                        "filepath": str(filepath),
                        "success": True
                    })
                else:
                    results.append({"section": section_name, "error": "생성 실패"})
            except Exception as e:
                results.append({"section": section_name, "error": str(e)[:50]})
        
        success_count = len([r for r in results if r.get("success")])
        
        self.phase = VoicePhase.CONFIRM
        self.status = AgentStatus.WAITING_FEEDBACK
        
        audio_list = "\n".join([
            f"  - {r[section]}: {성공 if r.get(success) else r.get(error, 실패)}"
            for r in results
        ])
        
        voice_type = {
            "default": "기본 보이스 (Sohee)",
            "youtube": f"YouTube 클로닝 ({self.youtube_url[:30]}...)",
            "sample": f"샘플 클로닝 ({self.sample_file})"
        }.get(self.voice_option, "알 수 없음")
        
        message = f"""보이스오버 생성이 완료되었습니다!

**음성 타입:** {voice_type}
**생성 결과:** {success_count}/{total} 섹션 성공

{audio_list}

음성 파일이 서버에 저장되었습니다.
확정을 입력하면 완료됩니다. 다시를 입력하면 재생성합니다."""
        
        return AgentResult(
            success=True,
            step="voiceover_done",
            message=message,
            data={
                "voice_option": self.voice_option,
                "sections": results,
                "success_count": success_count,
                "total_count": total
            },
            needs_feedback=True
        )
    
    def _extract_sections(self, script: Dict[str, Any]) -> List[tuple]:
        """스크립트에서 섹션별 텍스트 추출"""
        sections = []
        
        section_names = {
            "opening": "오프닝",
            "intro": "인트로",
            "body1": "본론1",
            "body2": "본론2",
            "body3": "본론3",
            "conclusion": "결론"
        }
        
        if isinstance(script, dict):
            for key, name in section_names.items():
                text = script.get(key, "")
                if text and len(text.strip()) > 10:
                    sections.append((name, text.strip()))
        elif isinstance(script, str):
            if len(script.strip()) > 10:
                sections.append(("전체", script.strip()))
        
        return sections
    
    async def _generate_default(self, text: str) -> Optional[str]:
        """기본 보이스(Sohee) 생성"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": text,
                    "language": self.DEFAULT_LANGUAGE,
                    "speaker": self.DEFAULT_SPEAKER,
                    "instruct": ""
                }
                
                async with session.post(
                    f"{self.TTS_CUSTOM_URL}/tts",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("audio_base64")
                    return None
        except Exception as e:
            print(f"Default TTS failed: {e}")
            return None
    
    async def _generate_clone(self, text: str, ref_audio_b64: str, ref_text: str = None) -> Optional[str]:
        """클로닝 보이스 생성"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": text,
                    "language": self.DEFAULT_LANGUAGE,
                    "ref_audio_base64": ref_audio_b64,
                    "ref_text": ref_text or "",
                    "x_vector_only_mode": not bool(ref_text)
                }
                
                async with session.post(
                    f"{self.TTS_BASE_URL}/clone",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("audio_base64")
                    else:
                        error = await response.text()
                        print(f"Clone TTS error: {error}")
                    return None
        except Exception as e:
            print(f"Clone TTS failed: {e}")
            return None
