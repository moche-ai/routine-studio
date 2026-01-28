"""영상 이미지 프롬프트 에이전트 - 대본에서 이미지/영상 프롬프트 생성"""

import sys
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum

sys.path.append("/app")

from agents.base import BaseAgent, AgentResult, AgentStatus
from apps.api.services.llm import llm_service


def emit_progress(status: str, detail: str = ""):
    """진행 상황 발생"""
    try:
        import builtins
        if hasattr(builtins, "emit_agent_progress"):
            builtins.emit_agent_progress(status, detail)
    except:
        pass


class PromptPhase(Enum):
    READY = "ready"
    GENERATING = "generating"
    REVIEW = "review"
    DONE = "done"


CHARACTER_TEMPLATES = {
    "finance_male": {
        "name": "금융 남성 캐릭터",
        "style": "Worzak-style financial cartoon",
        "description": "young Korean male, full body shot from head to toe, simple white or light background, bold black outlines, flat clean colors",
        "clothing": "simple casual outfit - plain t-shirt or hoodie, blue jeans, white sneakers",
    },
    "finance_female": {
        "name": "금융 여성 캐릭터",
        "style": "Worzak-style financial cartoon",
        "description": "young Korean female, full body shot from head to toe, simple white or light background, bold black outlines, flat clean colors",
        "clothing": "simple casual outfit - blouse or cardigan, jeans or skirt, comfortable shoes",
    }
}


SYSTEM_PROMPT = """너는 유튜브 금융 영상 전문 AI 비주얼 스토리보드 엔지니어야.

대본 한 줄을 받으면 다음을 생성해:
1. 이미지 프롬프트 (영어)
2. 영상 프롬프트 (영어)

🚨 이미지 프롬프트 필수 요구사항:
- 동일한 캐릭터의 전신 샷 (머리부터 발끝까지 완전히 보여야 함)
- 스타일: {style}
- 캐릭터 외모: {character_desc}
- 의상: {clothing}
- 배경: 흰색 또는 밝은 단색 배경
- 테두리: 굵은 검은색
- 색상: 깔끔하고 평면적
- 대본 내용에 맞는 과장된 얼굴 표정
- 소품은 필요시 최소한으로 (돈, 지폐, 영수증, 달러, 시계, 화살표, 차트)
- 이미지 안에 텍스트 없음 (자연스러운 것 제외)
- 썸네일로 바로 사용 가능한 깔끔한 구성

영상 프롬프트 규칙:
- 전신 캐릭터의 미세하고 자연스러운 움직임
- 허용: 눈 깜빡임, 호흡, 고개 살짝 기울임, 손/팔 작은 움직임
- 소품 애니메이션: 돈 살짝 떠다니기, 달력 넘기기, 시계 바늘 움직임
- 효과: 느린 줌인 또는 부드러운 패럴랙스
- 금지: 화면 흔들림, 빠른 편집, 캐릭터 잘림
- 캐릭터 디자인/의상/비율 일관성 유지
- 길이: 3-5초
- 분위기: 차분하고 깔끔

응답 형식 (JSON):
{{"image_prompt": "영어 이미지 프롬프트", "video_prompt": "영어 영상 프롬프트", "expression": "표정 설명 (한국어)", "props": ["사용된 소품 목록"]}}"""


class ImagePrompterAgent(BaseAgent):
    """영상 이미지 프롬프트 생성 에이전트"""
    
    def __init__(self):
        super().__init__("ImagePrompterAgent")
        self.phase = PromptPhase.READY
        self.character_type = "finance_male"
        self.generated_prompts: List[Dict] = []
        self.script_lines: List[str] = []
        self.current_index = 0
    
    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """텍스트에서 JSON 추출"""
        try:
            if "{" in text:
                start = text.find("{")
                depth = 0
                end = start
                for i, char in enumerate(text[start:], start):
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                json_str = text[start:end]
                return json.loads(json_str)
        except Exception as e:
            print(f"[ImagePrompter] JSON parse error: {e}")
        return None
    
    def _split_script(self, script_text: str) -> List[str]:
        """대본을 줄 단위로 분리"""
        lines = []
        sentences = re.split(r'(?<=[.!?])\s+', script_text.strip())
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 5:
                lines.append(sentence)
        return lines
    
    def _get_character_config(self) -> Dict[str, str]:
        """현재 캐릭터 설정 반환"""
        return CHARACTER_TEMPLATES.get(self.character_type, CHARACTER_TEMPLATES["finance_male"])
    
    async def _generate_prompt_for_line(self, line: str, line_num: int) -> Dict[str, Any]:
        """한 줄에 대한 이미지/영상 프롬프트 생성"""
        char_config = self._get_character_config()
        
        system_prompt = SYSTEM_PROMPT.format(
            style=char_config["style"],
            character_desc=char_config["description"],
            clothing=char_config["clothing"]
        )
        
        user_prompt = f"대본 줄: {line}\n\n위 대본에 맞는 이미지 프롬프트와 영상 프롬프트를 생성해줘. 캐릭터의 표정과 포즈가 대본 내용을 잘 표현해야 해."
        
        emit_progress(f"프롬프트 생성 중", f"{line_num}/{len(self.script_lines)}")
        
        try:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = await llm_service.generate(full_prompt, temperature=0.7, max_tokens=1024)
            result = self._parse_json(response)
            
            if result:
                return {
                    "line_num": line_num,
                    "script_line": line,
                    "image_prompt": result.get("image_prompt", ""),
                    "video_prompt": result.get("video_prompt", ""),
                    "expression": result.get("expression", ""),
                    "props": result.get("props", [])
                }
            else:
                return {
                    "line_num": line_num,
                    "script_line": line,
                    "image_prompt": "",
                    "video_prompt": "",
                    "expression": "",
                    "props": [],
                    "error": "JSON 파싱 실패"
                }
        except Exception as e:
            print(f"[ImagePrompter] Error: {e}")
            return {
                "line_num": line_num,
                "script_line": line,
                "image_prompt": "",
                "video_prompt": "",
                "expression": "",
                "props": [],
                "error": str(e)
            }
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """에이전트 시작"""
        self.status = AgentStatus.RUNNING
        self.phase = PromptPhase.READY
        
        script = input_data.get("script", {})
        script_text = ""
        
        if isinstance(script, dict):
            sections = script.get("sections", [])
            for section in sections:
                script_text += section.get("content", "") + "\n"
        elif isinstance(script, str):
            script_text = script
        
        char_info = input_data.get("character_info", {})
        if char_info.get("gender") == "female":
            self.character_type = "finance_female"
        else:
            self.character_type = "finance_male"
        
        if not script_text.strip():
            self.status = AgentStatus.WAITING_FEEDBACK
            return AgentResult(
                success=True,
                step="image_prompt",
                message="**영상 이미지 프롬프트 생성**\n\n대본을 입력해주세요. 각 문장마다 이미지/영상 프롬프트를 생성해드릴게요.\n\n대본을 붙여넣거나 직접 입력해주세요:",
                needs_feedback=True,
                data={"phase": "ready"}
            )
        
        return await self._start_generation(script_text)
    
    async def _start_generation(self, script_text: str) -> AgentResult:
        """프롬프트 생성 시작"""
        self.phase = PromptPhase.GENERATING
        self.script_lines = self._split_script(script_text)
        self.generated_prompts = []
        
        if not self.script_lines:
            return AgentResult(
                success=False,
                step="image_prompt",
                message="대본에서 문장을 찾을 수 없습니다. 다시 입력해주세요.",
                needs_feedback=True,
                data={"phase": "ready"}
            )
        
        emit_progress("프롬프트 생성 시작", f"총 {len(self.script_lines)}줄")
        
        for i, line in enumerate(self.script_lines, 1):
            prompt_data = await self._generate_prompt_for_line(line, i)
            self.generated_prompts.append(prompt_data)
        
        self.phase = PromptPhase.REVIEW
        result_text = self._format_results()
        
        self.status = AgentStatus.WAITING_FEEDBACK
        return AgentResult(
            success=True,
            step="image_prompt_review",
            message=result_text,
            needs_feedback=True,
            data={
                "phase": "review",
                "prompts": self.generated_prompts,
                "total_lines": len(self.script_lines)
            }
        )
    
    def _format_results(self) -> str:
        """생성된 프롬프트 포맷팅"""
        lines = ["# 영상 이미지 프롬프트 생성 완료\n"]
        lines.append(f"총 **{len(self.generated_prompts)}개** 장면의 프롬프트가 생성되었습니다.\n")
        lines.append("---\n")
        
        for prompt in self.generated_prompts:
            lines.append(f"### 장면 {prompt['line_num']}")
            lines.append(f"**대본:** {prompt['script_line']}\n")
            
            if prompt.get("expression"):
                lines.append(f"**표정:** {prompt['expression']}")
            
            if prompt.get("props"):
                lines.append(f"**소품:** {', '.join(prompt['props'])}")
            
            lines.append(f"\n**이미지 프롬프트:**\n```\n{prompt['image_prompt']}\n```\n")
            lines.append(f"**영상 프롬프트:**\n```\n{prompt['video_prompt']}\n```\n")
            lines.append("---\n")
        
        lines.append("\n프롬프트가 마음에 드시면 **확인**을 입력해주세요.")
        lines.append("수정이 필요하면 장면 번호와 수정 내용을 알려주세요. (예: \"3번 더 슬픈 표정으로\")")
        
        return "\n".join(lines)
    
    async def handle_feedback(self, feedback: str, images: List[str] = None) -> AgentResult:
        """피드백 처리"""
        feedback_lower = feedback.lower().strip()
        
        if self.phase == PromptPhase.READY:
            return await self._start_generation(feedback)
        
        elif self.phase == PromptPhase.REVIEW:
            if any(kw in feedback_lower for kw in ["확인", "완료", "ok", "좋아", "다음"]):
                self.phase = PromptPhase.DONE
                self.status = AgentStatus.COMPLETED
                
                return AgentResult(
                    success=True,
                    step="image_prompt_done",
                    message="프롬프트가 확정되었습니다!\n\n다음 단계로 진행합니다.",
                    needs_feedback=False,
                    data={
                        "phase": "done",
                        "prompts": self.generated_prompts
                    }
                )
            
            match = re.search(r"(\d+)번?\s*(.+)", feedback)
            if match:
                line_num = int(match.group(1))
                modification = match.group(2).strip()
                
                if 1 <= line_num <= len(self.generated_prompts):
                    return await self._modify_prompt(line_num, modification)
            
            if any(kw in feedback_lower for kw in ["다시", "재생성", "처음부터"]):
                self.phase = PromptPhase.READY
                return AgentResult(
                    success=True,
                    step="image_prompt",
                    message="대본을 다시 입력해주세요:",
                    needs_feedback=True,
                    data={"phase": "ready"}
                )
        
        return AgentResult(
            success=True,
            step="image_prompt_review",
            message="**확인**을 입력하거나, 수정할 장면 번호와 내용을 알려주세요.\n예: \"3번 더 밝은 표정으로\"",
            needs_feedback=True,
            data={"phase": self.phase.value}
        )
    
    async def _modify_prompt(self, line_num: int, modification: str) -> AgentResult:
        """특정 장면 프롬프트 수정"""
        emit_progress(f"장면 {line_num} 수정 중", modification[:30])
        
        original = self.generated_prompts[line_num - 1]
        char_config = self._get_character_config()
        
        system_prompt = SYSTEM_PROMPT.format(
            style=char_config["style"],
            character_desc=char_config["description"],
            clothing=char_config["clothing"]
        )
        
        user_prompt = f"""대본 줄: {original['script_line']}

기존 이미지 프롬프트: {original['image_prompt']}
기존 영상 프롬프트: {original['video_prompt']}

수정 요청: {modification}

위 수정 요청을 반영해서 프롬프트를 다시 생성해줘."""
        
        try:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = await llm_service.generate(full_prompt, temperature=0.7, max_tokens=1024)
            result = self._parse_json(response)
            
            if result:
                self.generated_prompts[line_num - 1] = {
                    "line_num": line_num,
                    "script_line": original["script_line"],
                    "image_prompt": result.get("image_prompt", original["image_prompt"]),
                    "video_prompt": result.get("video_prompt", original["video_prompt"]),
                    "expression": result.get("expression", ""),
                    "props": result.get("props", [])
                }
            
            result_text = self._format_results()
            
            return AgentResult(
                success=True,
                step="image_prompt_review",
                message=f"✏장면 {line_num}이 수정되었습니다!\n\n{result_text}",
                needs_feedback=True,
                data={
                    "phase": "review",
                    "prompts": self.generated_prompts,
                    "modified_line": line_num
                }
            )
        except Exception as e:
            return AgentResult(
                success=False,
                step="image_prompt_review",
                message=f"수정 중 오류가 발생했습니다: {e}\n\n다시 시도해주세요.",
                needs_feedback=True,
                data={"phase": "review"}
            )
