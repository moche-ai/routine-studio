"""
Audio Processing Library

음성 처리 및 화자 분리를 위한 라이브러리

Components:
- processor: 음성 전처리 (노이즈 제거, 최적 구간 추출)
- diarization: 화자 분리 (pyannote 기반) - torch 필요
"""

from .processor import (
    audio_processor,
    AudioProcessor,
    ProcessedAudio,
    AudioSegment,
)

__all__ = [
    # Processor
    "audio_processor",
    "AudioProcessor",
    "ProcessedAudio",
    "AudioSegment",
]

# Diarization은 torch가 있을 때만 import
try:
    from .diarization import (
        speaker_diarizer,
        SpeakerDiarizer,
        SpeakerSegment,
        DiarizationResult,
    )
    __all__.extend([
        "speaker_diarizer",
        "SpeakerDiarizer",
        "SpeakerSegment",
        "DiarizationResult",
    ])
except ImportError:
    pass
