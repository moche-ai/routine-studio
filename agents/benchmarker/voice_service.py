"""YouTube 음성 추출 및 Qwen3-TTS 음성 복제 서비스"""

import asyncio
import base64
import os
import re
import tempfile
from dataclasses import dataclass
from typing import Optional, Tuple, List

import httpx


@dataclass
class VoiceSample:
    """음성 샘플 결과"""
    audio_base64: str           # 생성된 음성 (base64 WAV)
    sample_rate: int            # 샘플레이트
    generation_time: float      # 생성 시간
    source_video_id: str        # 원본 영상 ID
    time_range: Tuple[int, int] # 추출 구간 (시작초, 끝초)
    ref_text: str               # 레퍼런스 텍스트
    generated_text: str         # 생성된 텍스트


class VoiceService:
    """YouTube 음성 추출 및 Qwen3-TTS 음성 복제"""
    
    def __init__(
        self, 
        tts_base_url: str = "http://localhost:8310",
        ytdlp_path: str = "yt-dlp",
        ffmpeg_path: str = "ffmpeg"
    ):
        self.tts_base_url = tts_base_url
        self.ytdlp_path = ytdlp_path
        self.ffmpeg_path = ffmpeg_path
    
    def _parse_time(self, time_str: str) -> int:
        """시간 문자열을 초로 변환 (MM:SS, M:SS, SS, HH:MM:SS)"""
        if isinstance(time_str, (int, float)):
            return int(time_str)
        
        parts = str(time_str).split(":")
        if len(parts) == 1:
            return int(parts[0])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """YouTube URL에서 비디오 ID 추출"""
        patterns = [
            r"youtube\.com/watch\?v=([^&]+)",
            r"youtu\.be/([^?]+)",
            r"youtube\.com/shorts/([^?]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def _run_command(self, cmd: List[str]) -> Tuple[bytes, bytes]:
        """명령 실행"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return stdout, stderr
    
    async def extract_audio_segment(
        self,
        video_url: str,
        start_time: str,
        end_time: str,
        output_format: str = "wav"
    ) -> Tuple[bytes, str]:
        """
        YouTube 영상에서 특정 구간 오디오 추출
        
        Args:
            video_url: YouTube 영상 URL
            start_time: 시작 시간 (MM:SS 또는 초)
            end_time: 종료 시간 (MM:SS 또는 초)
            output_format: 출력 포맷 (wav, mp3)
        
        Returns:
            (audio_bytes, video_id)
        """
        video_id = self._extract_video_id(video_url)
        if not video_id:
            raise ValueError(f"Invalid YouTube URL: {video_url}")
        
        start_sec = self._parse_time(start_time)
        end_sec = self._parse_time(end_time)
        duration = end_sec - start_sec
        
        if duration <= 0:
            raise ValueError(f"Invalid time range: {start_time} - {end_time}")
        
        if duration > 60:
            raise ValueError("Maximum duration is 60 seconds for voice cloning")
        
        # 임시 파일 경로
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, f"{video_id}_full.wav")
            segment_path = os.path.join(tmpdir, f"{video_id}_segment.{output_format}")
            
            # 1. yt-dlp로 오디오 다운로드
            ytdlp_cmd = [
                self.ytdlp_path,
                "-x",  # 오디오만 추출
                "--audio-format", "wav",
                "--audio-quality", "0",  # 최고 품질
                "-o", audio_path,
                "--no-playlist",
                video_url
            ]
            
            stdout, stderr = await self._run_command(ytdlp_cmd)
            
            # yt-dlp는 확장자를 자동으로 붙일 수 있음
            if not os.path.exists(audio_path):
                # .wav 확장자가 추가된 경우
                if os.path.exists(audio_path + ".wav"):
                    audio_path = audio_path + ".wav"
                else:
                    # 다른 포맷으로 저장된 경우 찾기
                    for f in os.listdir(tmpdir):
                        if f.startswith(video_id):
                            audio_path = os.path.join(tmpdir, f)
                            break
            
            if not os.path.exists(audio_path):
                raise RuntimeError(f"Failed to download audio: {stderr.decode()}")
            
            # 2. ffmpeg로 구간 추출
            ffmpeg_cmd = [
                self.ffmpeg_path,
                "-i", audio_path,
                "-ss", str(start_sec),
                "-t", str(duration),
                "-ar", "24000",  # Qwen3-TTS 권장 샘플레이트
                "-ac", "1",      # 모노
                "-y",            # 덮어쓰기
                segment_path
            ]
            
            stdout, stderr = await self._run_command(ffmpeg_cmd)
            
            if not os.path.exists(segment_path):
                raise RuntimeError(f"Failed to extract segment: {stderr.decode()}")
            
            # 3. 파일 읽기
            with open(segment_path, "rb") as f:
                audio_bytes = f.read()
            
            return audio_bytes, video_id
    
    async def get_transcript_segment(
        self,
        video_url: str,
        start_time: str,
        end_time: str,
        lang_priority: List[str] = None
    ) -> Optional[str]:
        """
        YouTube 영상의 특정 구간 자막 추출
        
        Args:
            video_url: YouTube 영상 URL
            start_time: 시작 시간
            end_time: 종료 시간
            lang_priority: 언어 우선순위
        
        Returns:
            해당 구간의 자막 텍스트
        """
        if lang_priority is None:
            lang_priority = ["ko", "en", "en-US", "ko-KR"]
        
        video_id = self._extract_video_id(video_url)
        if not video_id:
            return None
        
        start_sec = self._parse_time(start_time)
        end_sec = self._parse_time(end_time)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 자막 다운로드
            sub_path = os.path.join(tmpdir, "sub")
            
            ytdlp_cmd = [
                self.ytdlp_path,
                "--write-sub",
                "--write-auto-sub",
                "--sub-lang", ",".join(lang_priority),
                "--skip-download",
                "--sub-format", "vtt",
                "-o", sub_path,
                video_url
            ]
            
            await self._run_command(ytdlp_cmd)
            
            # 자막 파일 찾기
            vtt_content = None
            for lang in lang_priority:
                for suffix in ["", "-orig"]:
                    vtt_path = f"{sub_path}.{lang}{suffix}.vtt"
                    if os.path.exists(vtt_path):
                        with open(vtt_path, "r", encoding="utf-8") as f:
                            vtt_content = f.read()
                        break
                if vtt_content:
                    break
            
            if not vtt_content:
                return None
            
            # VTT 파싱 - 시간 범위에 해당하는 텍스트 추출
            return self._extract_vtt_segment(vtt_content, start_sec, end_sec)
    
    def _extract_vtt_segment(self, vtt_content: str, start_sec: int, end_sec: int) -> str:
        """VTT 자막에서 특정 시간 구간의 텍스트 추출"""
        lines = []
        current_time = 0
        
        for line in vtt_content.split("\n"):
            # 타임스탬프 라인 파싱: 00:00:05.000 --> 00:00:08.000
            time_match = re.match(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})", line)
            if time_match:
                h1, m1, s1 = int(time_match.group(1)), int(time_match.group(2)), int(time_match.group(3))
                h2, m2, s2 = int(time_match.group(5)), int(time_match.group(6)), int(time_match.group(7))
                
                line_start = h1 * 3600 + m1 * 60 + s1
                line_end = h2 * 3600 + m2 * 60 + s2
                
                # 구간과 겹치는지 확인
                if line_start < end_sec and line_end > start_sec:
                    current_time = line_start
                else:
                    current_time = -1  # 범위 밖
                continue
            
            # WEBVTT 헤더 등 스킵
            if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            
            # 빈 줄 스킵
            if not line.strip():
                continue
            
            # 숫자만 있는 라인 스킵 (큐 번호)
            if line.strip().isdigit():
                continue
            
            # 현재 시간이 범위 내이면 텍스트 추가
            if current_time >= 0:
                # HTML 태그 제거
                clean_line = re.sub(r"<[^>]+>", "", line)
                if clean_line.strip():
                    lines.append(clean_line.strip())
        
        # 중복 제거 (자동 자막에서 흔함)
        seen = set()
        unique_lines = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        
        return " ".join(unique_lines)
    
    async def clone_voice(
        self,
        text: str,
        ref_audio_base64: str,
        ref_text: str = "",
        language: str = "Korean",
        x_vector_only_mode: bool = True  # True = no prompt leak
    ) -> dict:
        """
        Qwen3-TTS API로 음성 복제
        
        Args:
            text: 생성할 텍스트
            ref_audio_base64: 레퍼런스 오디오 (base64)
            ref_text: 레퍼런스 오디오의 텍스트 (x_vector_only_mode=True면 불필요)
            language: 언어 (Korean, English, etc.)
            x_vector_only_mode: True면 speaker embedding만 사용 (prompt leak 방지)
        
        Returns:
            {audio_base64, sample_rate, generation_time}
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.tts_base_url}/clone",
                json={
                    "text": text,
                    "language": language,
                    "ref_audio_base64": ref_audio_base64,
                    "ref_text": ref_text,
                    "x_vector_only_mode": x_vector_only_mode
                }
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"TTS API error: {response.text}")
            
            return response.json()
    
    async def create_voice_sample(
        self,
        video_url: str,
        start_time: str,
        end_time: str,
        generate_text: str,
        ref_text: Optional[str] = None,
        language: str = "Korean"
    ) -> VoiceSample:
        """
        YouTube 영상에서 음성 추출 후 복제 샘플 생성
        
        Args:
            video_url: YouTube 영상 URL
            start_time: 레퍼런스 구간 시작 (예: "1:30" 또는 90)
            end_time: 레퍼런스 구간 끝 (예: "1:45" 또는 105)
            generate_text: 생성할 텍스트
            ref_text: 레퍼런스 구간의 텍스트 (없으면 자막에서 자동 추출)
            language: 언어
        
        Returns:
            VoiceSample
        """
        start_sec = self._parse_time(start_time)
        end_sec = self._parse_time(end_time)
        
        # 1. 오디오 세그먼트 추출
        print(f"Extracting audio segment from {video_url} ({start_time} - {end_time})...")
        audio_bytes, video_id = await self.extract_audio_segment(
            video_url, start_time, end_time
        )
        ref_audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        # 2. ref_text가 없으면 자막에서 추출 시도
        if not ref_text:
            print("Extracting transcript for reference...")
            ref_text = await self.get_transcript_segment(
                video_url, start_time, end_time
            )
            if not ref_text:
                raise ValueError(
                    "Could not extract transcript. Please provide ref_text manually."
                )
        
        print(f"Reference text: {ref_text[:100]}...")
        
        # 3. 음성 복제
        print(f"Generating voice clone for: {generate_text[:50]}...")
        result = await self.clone_voice(
            text=generate_text,
            ref_audio_base64=ref_audio_base64,
            ref_text=ref_text,
            language=language
        )
        
        return VoiceSample(
            audio_base64=result["audio_base64"],
            sample_rate=result["sample_rate"],
            generation_time=result["generation_time"],
            source_video_id=video_id,
            time_range=(start_sec, end_sec),
            ref_text=ref_text,
            generated_text=generate_text
        )
    
    async def check_health(self) -> dict:
        """TTS 서비스 헬스 체크"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.tts_base_url}/health")
            return response.json()


# 싱글톤 인스턴스
voice_service = VoiceService()


# ============================================
# Auto-preprocessing integration
# ============================================

from libs.audio import audio_processor, ProcessedAudio


class VoiceServiceV2(VoiceService):
    """음성 서비스 확장 - 자동 전처리 포함"""
    
    async def create_voice_sample_auto(
        self,
        video_url: str,
        start_time: str,
        end_time: str,
        generate_text: str,
        ref_text: Optional[str] = None,
        language: str = "Korean",
        auto_preprocess: bool = True,
        target_duration: float = 5.0
    ) -> Tuple[VoiceSample, Optional[ProcessedAudio]]:
        """
        음성 샘플 생성 (자동 전처리 포함)
        
        Args:
            video_url: YouTube URL
            start_time: 시작 시간
            end_time: 종료 시간
            generate_text: 생성할 텍스트
            ref_text: 레퍼런스 텍스트 (None이면 자막에서 추출)
            language: 언어
            auto_preprocess: 자동 전처리 여부
            target_duration: 목표 레퍼런스 길이 (3-10초)
        
        Returns:
            (VoiceSample, ProcessedAudio or None)
        """
        start_sec = self._parse_time(start_time)
        end_sec = self._parse_time(end_time)
        
        # 1. 오디오 추출
        print(f"Extracting audio from {video_url} ({start_time} - {end_time})...")
        audio_bytes, video_id = await self.extract_audio_segment(
            video_url, start_time, end_time
        )
        
        # 2. 자동 전처리
        processed = None
        if auto_preprocess:
            print(f"Auto-preprocessing audio (target: {target_duration}s)...")
            processed = await audio_processor.preprocess_for_cloning(
                audio_bytes,
                target_duration=target_duration,
                normalize=True
            )
            audio_bytes = processed.audio_bytes
            print(f"  Original: {processed.original_duration:.1f}s -> Processed: {processed.duration:.1f}s")
            print(f"  Selected range: {processed.selected_range[0]:.1f}s - {processed.selected_range[1]:.1f}s")
        
        ref_audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        # 3. ref_text 추출
        if not ref_text:
            print("Extracting transcript for reference...")
            # 전처리된 구간에 맞춰 자막 추출
            if processed:
                actual_start = start_sec + processed.selected_range[0]
                actual_end = start_sec + processed.selected_range[1]
            else:
                actual_start = start_sec
                actual_end = end_sec
            
            ref_text = await self.get_transcript_segment(
                video_url,
                str(int(actual_start)),
                str(int(actual_end))
            )
            
            if not ref_text:
                raise ValueError(
                    "Could not extract transcript. Please provide ref_text manually."
                )
        
        print(f"Reference text: {ref_text[:100]}...")
        
        # 4. 음성 복제
        print(f"Generating voice clone for: {generate_text[:50]}...")
        result = await self.clone_voice(
            text=generate_text,
            ref_audio_base64=ref_audio_base64,
            ref_text=ref_text,
            language=language
        )
        
        sample = VoiceSample(
            audio_base64=result["audio_base64"],
            sample_rate=result["sample_rate"],
            generation_time=result["generation_time"],
            source_video_id=video_id,
            time_range=(start_sec, end_sec),
            ref_text=ref_text,
            generated_text=generate_text
        )
        
        return sample, processed
    
    async def smart_extract_and_clone(
        self,
        video_url: str,
        approximate_time: str,
        generate_text: str,
        ref_text: Optional[str] = None,
        language: str = "Korean",
        search_window: int = 30
    ) -> Tuple[VoiceSample, ProcessedAudio]:
        """
        스마트 추출 - 대략적인 시간 주변에서 최적 구간 자동 탐색
        
        Args:
            video_url: YouTube URL
            approximate_time: 대략적인 시간 (이 주변에서 탐색)
            generate_text: 생성할 텍스트
            ref_text: 레퍼런스 텍스트
            language: 언어
            search_window: 탐색 범위 (초, 앞뒤로)
        
        Returns:
            (VoiceSample, ProcessedAudio)
        """
        center_sec = self._parse_time(approximate_time)
        
        # 탐색 범위 설정
        start_sec = max(0, center_sec - search_window)
        end_sec = center_sec + search_window
        
        print(f"Smart extraction: searching around {approximate_time} (±{search_window}s)...")
        
        # 넓은 범위 추출
        audio_bytes, video_id = await self.extract_audio_segment(
            video_url,
            str(start_sec),
            str(end_sec)
        )
        
        # 자동 전처리로 최적 구간 찾기
        processed = await audio_processor.preprocess_for_cloning(
            audio_bytes,
            target_duration=5.0,
            normalize=True
        )
        
        print(f"Found optimal segment: {processed.selected_range[0]:.1f}s - {processed.selected_range[1]:.1f}s")
        print(f"Duration: {processed.duration:.1f}s")
        
        ref_audio_base64 = base64.b64encode(processed.audio_bytes).decode("utf-8")
        
        # 자막 추출
        if not ref_text:
            actual_start = start_sec + processed.selected_range[0]
            actual_end = start_sec + processed.selected_range[1]
            
            ref_text = await self.get_transcript_segment(
                video_url,
                str(int(actual_start)),
                str(int(actual_end))
            )
            
            if not ref_text:
                raise ValueError("Could not extract transcript. Please provide ref_text.")
        
        # 음성 복제
        result = await self.clone_voice(
            text=generate_text,
            ref_audio_base64=ref_audio_base64,
            ref_text=ref_text,
            language=language
        )
        
        sample = VoiceSample(
            audio_base64=result["audio_base64"],
            sample_rate=result["sample_rate"],
            generation_time=result["generation_time"],
            source_video_id=video_id,
            time_range=(
                int(start_sec + processed.selected_range[0]),
                int(start_sec + processed.selected_range[1])
            ),
            ref_text=ref_text,
            generated_text=generate_text
        )
        
        return sample, processed


# V2 싱글톤
voice_service_v2 = VoiceServiceV2()
