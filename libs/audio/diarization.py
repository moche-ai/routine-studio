"""Speaker Diarization 서비스 v3 - pyannote 4.0 API"""

import asyncio
import os
import tempfile
from dataclasses import dataclass
from typing import List, Optional

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


@dataclass
class SpeakerSegment:
    speaker: str
    start: float
    end: float
    duration: float


@dataclass
class DiarizationResult:
    segments: List[SpeakerSegment]
    speakers: List[str]
    speaker_durations: dict
    total_duration: float


class SpeakerDiarizer:
    def __init__(self, hf_token: str = None):
        if not TORCH_AVAILABLE:
            raise ImportError("torch is required for SpeakerDiarizer")
        self.hf_token = hf_token or os.environ.get("HF_TOKEN")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._pipeline = None

    def _load_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        from pyannote.audio import Pipeline
        print(f"Loading pyannote/speaker-diarization-3.1 on {self.device}...")

        self._pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=self.hf_token
        )
        self._pipeline.to(torch.device(self.device))
        print("Pipeline loaded!")
        return self._pipeline

    async def diarize(self, audio_path: str, max_speakers: int = None) -> DiarizationResult:
        pipeline = self._load_pipeline()

        params = {}
        if max_speakers:
            params["max_speakers"] = max_speakers

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, lambda: pipeline(audio_path, **params))

        # pyannote 4.0: output.speaker_diarization
        diarization = output.speaker_diarization

        segments = []
        speaker_durations = {}

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            duration = turn.end - turn.start
            segments.append(SpeakerSegment(
                speaker=speaker,
                start=turn.start,
                end=turn.end,
                duration=duration
            ))
            speaker_durations[speaker] = speaker_durations.get(speaker, 0) + duration

        speakers = list(speaker_durations.keys())
        total_duration = max(s.end for s in segments) if segments else 0

        return DiarizationResult(
            segments=segments,
            speakers=speakers,
            speaker_durations=speaker_durations,
            total_duration=total_duration
        )

    def get_main_speaker(self, result: DiarizationResult) -> str:
        if not result.speaker_durations:
            return None
        return max(result.speaker_durations, key=result.speaker_durations.get)

    def get_best_segment(self, result: DiarizationResult, speaker: str,
                         min_dur: float = 3.0, max_dur: float = 7.0) -> Optional[SpeakerSegment]:
        segments = [s for s in result.segments if s.speaker == speaker and s.duration >= min_dur]

        if not segments:
            segments = [s for s in result.segments if s.speaker == speaker]
            if segments:
                return max(segments, key=lambda s: s.duration)
            return None

        candidates = [s for s in segments if s.duration <= max_dur]
        if candidates:
            return min(candidates, key=lambda s: abs(s.duration - 5.0))

        longest = max(segments, key=lambda s: s.duration)
        return SpeakerSegment(speaker=longest.speaker, start=longest.start,
                              end=longest.start + max_dur, duration=max_dur)


# 싱글톤은 torch가 있을 때만 생성
speaker_diarizer = None
if TORCH_AVAILABLE:
    try:
        speaker_diarizer = SpeakerDiarizer(
            hf_token=os.environ.get("HF_TOKEN")
        )
    except Exception:
        pass
