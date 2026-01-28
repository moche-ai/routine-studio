import os

"""TTS Preview Service - 음성 미리듣기 서비스"""

import asyncio
import base64
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

import aiohttp


# === Error Classes ===


class TTSError(Exception):
    """TTS 관련 에러"""

    def __init__(
        self, message: str, user_message: str = None, fallback_suggestion: bool = True
    ):
        self.message = message
        self.user_message = user_message or message
        self.fallback_suggestion = fallback_suggestion
        super().__init__(message)


# === Rate Limiter ===


class RateLimiter:
    """세션별 Rate Limiting (3 requests per 10 seconds)"""

    def __init__(self, max_requests: int = 3, time_window: int = 10):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, session_id: str) -> bool:
        """요청 허용 여부 확인"""
        now = time.time()
        # 오래된 요청 제거
        self.requests[session_id] = [
            t for t in self.requests[session_id] if now - t < self.time_window
        ]

        if len(self.requests[session_id]) >= self.max_requests:
            return False

        self.requests[session_id].append(now)
        return True

    def get_wait_time(self, session_id: str) -> float:
        """다음 요청까지 대기 시간"""
        if not self.requests[session_id]:
            return 0

        oldest = min(self.requests[session_id])
        wait = self.time_window - (time.time() - oldest)
        return max(0, wait)


# === TTS Preview Service ===


@dataclass
class VoiceSample:
    """음성 샘플 정보"""

    voice_id: str
    filename: str
    prompt_text: str
    description: str = ""


@dataclass
class TTSResult:
    """TTS 생성 결과"""

    audio_base64: str
    duration: float
    voice_name: str
    text: str


class TTSPreviewService:
    """TTS 미리듣기 서비스"""

    # TTS 서버 설정
    TTS_CUSTOM_URL = os.environ.get(
        "TTS_API_URL", "http://172.17.0.1:8311"
    )  # 프리셋 보이스 (Sohee 등)
    TTS_BASE_URL = os.environ.get("TTS_CLONE_URL", "http://172.17.0.1:8310")  # 클로닝

    # 샘플 디렉토리
    # Full 버전 샘플 사용 (cut 버전 아님)
    SAMPLES_DIR = Path("/data/volumes/routine/youtube-studio/voices/samples")
    SAMPLES_JSON = Path(
        "/data/volumes/routine/youtube-studio/voices/samples_cut_prompts.json"
    )

    # 기본 설정
    DEFAULT_SPEAKER = "Sohee"
    DEFAULT_LANGUAGE = "Korean"
    DEFAULT_TEST_TEXT = "안녕하세요 {channel_name} 입니다. 루틴 스튜디오로 함께 만들어보는 유튜브 영상 제작 프로세스 입니다."

    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=3, time_window=10)
        self._samples_cache: Optional[List[Dict]] = None

    def check_rate_limit(self, session_id: str) -> bool:
        """Rate limit 체크"""
        return self.rate_limiter.is_allowed(session_id)

    def get_rate_limit_wait_time(self, session_id: str) -> float:
        """대기 시간 반환"""
        return self.rate_limiter.get_wait_time(session_id)

    # === Sample Voice Methods ===

    def _load_samples(self) -> List[Dict]:
        """샘플 목록 로드 (캐시)"""
        if self._samples_cache is not None:
            return self._samples_cache

        if not self.SAMPLES_JSON.exists():
            return []

        try:
            with open(self.SAMPLES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._samples_cache = data.get("prompts", [])
                return self._samples_cache
        except Exception:
            return []

    def get_voice_samples(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """음성 샘플 목록 반환 (페이지네이션)"""
        samples = self._load_samples()

        total = len(samples)
        start = (page - 1) * per_page
        end = start + per_page

        page_samples = []
        for i, s in enumerate(samples[start:end], start=start):
            page_samples.append(
                {
                    "voice_id": s.get("filename", f"sample_{i}")
                    .replace(".mp3", "")
                    .replace(".wav", ""),
                    "filename": s.get("filename", ""),
                    "prompt_text": s.get("prompt_text", "")[:100],
                    "index": i,
                }
            )

        return {
            "samples": page_samples,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    def get_sample_audio(self, voice_id: str) -> Optional[str]:
        """특정 샘플의 오디오 반환 (base64) - full 버전 우선"""
        import re

        base_id = re.sub(r"_\d+$", "", voice_id)

        for ext in [".mp3", ".wav"]:
            full_path = self.SAMPLES_DIR / (base_id + ext)
            if full_path.exists():
                try:
                    with open(full_path, "rb") as f:
                        return base64.b64encode(f.read()).decode("utf-8")
                except Exception:
                    pass

        samples = self._load_samples()
        sample = None
        for s in samples:
            filename = s.get("filename", "")
            if (
                voice_id in filename
                or filename.replace(".mp3", "").replace(".wav", "") == voice_id
            ):
                sample = s
                break

        if not sample:
            return None

        filename = sample.get("filename", "")
        audio_path = self.SAMPLES_DIR / filename

        if not audio_path.exists():
            for ext in [".mp3", ".wav"]:
                test_path = self.SAMPLES_DIR / (voice_id + ext)
                if test_path.exists():
                    audio_path = test_path
                    break

        if not audio_path.exists():
            return None

        try:
            with open(audio_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return None

    def get_sample_info(self, voice_id: str) -> Optional[Dict]:
        """샘플 정보 반환"""
        samples = self._load_samples()

        for s in samples:
            filename = s.get("filename", "")
            if (
                voice_id in filename
                or filename.replace(".mp3", "").replace(".wav", "") == voice_id
            ):
                return {
                    "voice_id": voice_id,
                    "filename": filename,
                    "prompt_text": s.get("prompt_text", ""),
                }
        return None

    # === TTS Generation Methods ===

    async def generate_preview(
        self,
        text: str,
        speaker: str = None,
        session_id: str = None,
        instruct: str = None,
        speed: float = None,
        pitch: int = None,
    ) -> TTSResult:
        """기본 보이스로 TTS 미리듣기 생성

        Args:
            text: 변환할 텍스트
            speaker: 화자 이름 (기본: Sohee)
            session_id: 세션 ID
            instruct: 감정/스타일 지시 (예: "슬프게", "신나게", "차분하게")
            speed: 속도 조절 (0.5-2.0, 기본 1.0)
            pitch: 피치 조절 (-20 to +20, 기본 0)
        """
        speaker = speaker or self.DEFAULT_SPEAKER
        instruct = instruct or ""

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": text,
                    "language": self.DEFAULT_LANGUAGE,
                    "speaker": speaker,
                    "instruct": instruct,  # Now using the parameter
                }

                async with session.post(
                    f"{self.TTS_CUSTOM_URL}/tts",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        audio_base64 = data.get("audio_base64", "")

                        # Apply speed/pitch post-processing if specified
                        if audio_base64 and (speed is not None or pitch is not None):
                            audio_base64 = await self._apply_audio_effects(
                                audio_base64, speed=speed, pitch=pitch
                            )

                        # Duration calculation
                        audio_bytes = (
                            len(base64.b64decode(audio_base64)) if audio_base64 else 0
                        )
                        duration = audio_bytes / 48000

                        # Adjust duration estimate for speed
                        if speed is not None and speed > 0:
                            duration = duration / speed

                        return TTSResult(
                            audio_base64=audio_base64,
                            duration=round(duration, 2),
                            voice_name=speaker,
                            text=text,
                        )
                    else:
                        error_text = await response.text()
                        raise TTSError(
                            f"TTS 서버 오류: {error_text}",
                            "음성 생성에 실패했습니다. 샘플 보이스를 들어보시겠어요?",
                        )
        except aiohttp.ClientError as e:
            raise TTSError(
                f"TTS 서버 연결 실패: {str(e)}",
                "음성 서버에 연결할 수 없습니다. 샘플 보이스를 들어보시겠어요?",
            )

    async def _apply_audio_effects(
        self, audio_base64: str, speed: float = None, pitch: int = None
    ) -> str:
        """오디오에 속도/피치 효과 적용 (pydub 사용)"""
        try:
            from pydub import AudioSegment
            import io

            # Base64 -> AudioSegment
            audio_bytes = base64.b64decode(audio_base64)
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")

            # Apply speed change
            if speed is not None and speed != 1.0:
                # Clamp speed between 0.5 and 2.0
                speed = max(0.5, min(2.0, speed))
                # Change speed without changing pitch
                sound_with_altered_frame_rate = audio._spawn(
                    audio.raw_data,
                    overrides={"frame_rate": int(audio.frame_rate * speed)},
                )
                audio = sound_with_altered_frame_rate.set_frame_rate(audio.frame_rate)

            # Apply pitch change (semitones)
            if pitch is not None and pitch != 0:
                # Clamp pitch between -20 and +20
                pitch = max(-20, min(20, pitch))
                # Pitch shift using frame rate manipulation
                new_sample_rate = int(audio.frame_rate * (2 ** (pitch / 12.0)))
                audio = audio._spawn(
                    audio.raw_data, overrides={"frame_rate": new_sample_rate}
                ).set_frame_rate(audio.frame_rate)

            # AudioSegment -> Base64
            buffer = io.BytesIO()
            audio.export(buffer, format="wav")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")

        except ImportError:
            # pydub not installed, return original
            print("[TTS] pydub not installed, skipping audio effects")
            return audio_base64
        except Exception as e:
            print(f"[TTS] Audio effect error: {e}")
            return audio_base64

    async def clone_voice_preview(
        self,
        text: str,
        ref_audio_base64: str,
        ref_text: str = None,
        session_id: str = None,
    ) -> TTSResult:
        """보이스 클로닝으로 TTS 미리듣기 생성"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": text,
                    "language": self.DEFAULT_LANGUAGE,
                    "ref_audio_base64": ref_audio_base64,
                    "ref_text": ref_text or "",
                    "x_vector_only_mode": True,
                }

                async with session.post(
                    f"{self.TTS_BASE_URL}/clone",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        audio_base64 = data.get("audio_base64", "")

                        audio_bytes = (
                            len(base64.b64decode(audio_base64)) if audio_base64 else 0
                        )
                        duration = audio_bytes / 48000

                        return TTSResult(
                            audio_base64=audio_base64,
                            duration=round(duration, 2),
                            voice_name="클로닝 보이스",
                            text=text,
                        )
                    else:
                        error_text = await response.text()
                        raise TTSError(
                            f"클로닝 서버 오류: {error_text}",
                            "보이스 클로닝에 실패했습니다. 기본 보이스를 사용해보시겠어요?",
                        )
        except aiohttp.ClientError as e:
            raise TTSError(
                f"클로닝 서버 연결 실패: {str(e)}",
                "클로닝 서버에 연결할 수 없습니다. 기본 보이스를 사용해보시겠어요?",
            )

    # === YouTube Extraction ===

    async def extract_youtube_audio(
        self, url: str, start_time: str, end_time: str, session_id: str = None
    ) -> Dict[str, Any]:
        """YouTube에서 오디오 추출"""
        try:
            # VoiceServiceV2 사용
            from agents.benchmarker.voice_service import voice_service

            audio_bytes, video_id = await voice_service.extract_audio_segment(
                url, start_time, end_time
            )

            # 오디오 전처리 (최적 구간 추출)
            from libs.audio.processor import audio_processor

            processed = await audio_processor.preprocess_for_cloning(
                audio_bytes, normalize=True, denoise=True
            )

            audio_base64 = base64.b64encode(processed.audio_bytes).decode("utf-8")

            # 자막 추출 시도
            ref_text = ""
            try:
                ref_text = await voice_service.get_transcript_segment(
                    url, start_time, end_time
                )
            except Exception:
                pass

            return {
                "audio_base64": audio_base64,
                "duration": processed.duration,
                "video_id": video_id,
                "ref_text": ref_text,
                "quality_score": processed.quality_score,
            }

        except Exception as e:
            raise TTSError(
                f"YouTube 추출 실패: {str(e)}",
                "YouTube에서 음성을 추출할 수 없습니다. URL과 시간대를 확인해주세요.",
            )

    def get_default_test_text(self, channel_name: str = "채널") -> str:
        """기본 테스트 문장 반환"""
        return self.DEFAULT_TEST_TEXT.format(channel_name=channel_name)


# 싱글톤 인스턴스
tts_preview_service = TTSPreviewService()
