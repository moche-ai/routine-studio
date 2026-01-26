# Audio Processing Library

음성 복제(Voice Cloning)를 위한 오디오 처리 라이브러리

## 설치 요구사항

```bash
# 필수
pip install numpy

# Speaker Diarization (선택)
pip install pyannote.audio torch

# HuggingFace 모델 접근 필요
# https://huggingface.co/pyannote/speaker-diarization-3.1
# https://huggingface.co/pyannote/segmentation-3.0
```

## 컴포넌트

### 1. AudioProcessor (processor.py)

음성 복제를 위한 오디오 전처리

**기능:**
- 음성/음악/노이즈 구분 (Spectral 분석)
- ffmpeg afftdn 노이즈 제거
- 최적 음성 구간 자동 추출 (3-7초)
- 볼륨 정규화

**사용법:**
```python
from libs.audio import audio_processor

# 전처리 (노이즈 제거 + 최적 구간 추출)
result = await audio_processor.preprocess_for_cloning(
    audio_bytes,
    target_duration=5.0,  # 목표 길이
    denoise=True,         # 노이즈 제거
    denoise_strength=0.4  # 강도 (0.0~1.0)
)

print(f"Duration: {result.duration}s")
print(f"Quality: {result.quality_score}")
print(f"Selected: {result.selected_range}")
```

**분석 지표:**
- Energy (RMS)
- Zero-Crossing Rate
- Spectral Centroid
- Voice Band Ratio (85-3400Hz)
- Spectral Flatness

### 2. SpeakerDiarizer (diarization.py)

pyannote 기반 다중 화자 분리

**기능:**
- 오디오에서 화자 자동 분리
- 화자별 발화 구간 추출
- 주요 화자 자동 선택
- 클로닝용 최적 구간 추천

**사용법:**
```python
import os
os.environ["HF_TOKEN"] = "hf_xxx"  # HuggingFace 토큰

from libs.audio import speaker_diarizer

# 화자 분리
result = await speaker_diarizer.diarize(
    audio_path,
    max_speakers=4
)

print(f"Speakers: {result.speakers}")
for spk, dur in result.speaker_durations.items():
    print(f"  {spk}: {dur:.1f}s")

# 주요 화자
main = speaker_diarizer.get_main_speaker(result)

# 클로닝용 최적 구간 (3-7초)
segment = speaker_diarizer.get_best_segment(result, main)
print(f"Best: {segment.start:.1f}s - {segment.end:.1f}s")
```

## 전체 워크플로우 예시

```python
import asyncio
from libs.audio import audio_processor, speaker_diarizer

async def process_for_cloning(audio_bytes: bytes):
    # 1. 임시 파일 저장
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        temp_path = f.name

    # 2. 화자 분리
    result = await speaker_diarizer.diarize(temp_path)
    main_speaker = speaker_diarizer.get_main_speaker(result)
    segment = speaker_diarizer.get_best_segment(result, main_speaker)

    # 3. 해당 구간 추출
    # ... (구간 추출 로직)

    # 4. 전처리
    processed = await audio_processor.preprocess_for_cloning(
        speaker_audio,
        denoise=True
    )

    return processed.audio_bytes
```

## 모델 저장 위치

```
/data/routine/routine-studio-v2/models/
├── pyannote-diarization-3.1/  # Speaker Diarization
├── speaker-embedding/          # SpeechBrain ECAPA
└── vad/                        # Voice Activity Detection
```

## 라이센스

- pyannote: MIT License
- speechbrain: Apache 2.0
