"""벤치마킹 에이전트 모듈"""

from .agent import BenchmarkerAgent
from .schemas import (
    BenchmarkPhase,
    VideoMetadata,
    ChannelMetadata,
    ThumbnailPattern,
    ScriptPattern,
    ContentStrategy,
    AudienceProfile,
    BenchmarkReport,
)
from .youtube_service import youtube_service, YouTubeService
from .screenshot_service import screenshot_service, ScreenshotService, ChannelScreenshot
from .voice_service import voice_service, VoiceService, VoiceSample, voice_service_v2, VoiceServiceV2

# libs/audio에서 import (하위 호환성)
from libs.audio import (
    audio_processor, AudioProcessor, ProcessedAudio, AudioSegment,
    speaker_diarizer, SpeakerDiarizer, SpeakerSegment, DiarizationResult,
)

__all__ = [
    # Agent
    "BenchmarkerAgent",
    # Schemas
    "BenchmarkPhase",
    "VideoMetadata",
    "ChannelMetadata",
    "ThumbnailPattern",
    "ScriptPattern",
    "ContentStrategy",
    "AudienceProfile",
    "BenchmarkReport",
    # YouTube
    "youtube_service",
    "YouTubeService",
    # Screenshot
    "screenshot_service",
    "ScreenshotService",
    "ChannelScreenshot",
    # Voice
    "voice_service",
    "VoiceService",
    "VoiceSample",
    "voice_service_v2",
    "VoiceServiceV2",
    # Audio (from libs.audio)
    "audio_processor",
    "AudioProcessor",
    "ProcessedAudio",
    "AudioSegment",
    "speaker_diarizer",
    "SpeakerDiarizer",
    "SpeakerSegment",
    "DiarizationResult",
]
