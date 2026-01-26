"""Audio Library Tests"""
import asyncio
import os
import sys

sys.path.insert(0, "/data/routine/routine-studio-v2")
# HF_TOKEN should be set in environment
# os.environ["HF_TOKEN"] = "your_token_here"


def test_import():
    """Import 테스트"""
    from libs.audio import audio_processor, speaker_diarizer
    from libs.audio import AudioProcessor, SpeakerDiarizer
    from libs.audio import ProcessedAudio, AudioSegment
    from libs.audio import SpeakerSegment, DiarizationResult
    print("✓ Import OK")


def test_audio_processor():
    """AudioProcessor 테스트"""
    from libs.audio import audio_processor
    
    # 테스트용 WAV 생성 (1초 사인파)
    import numpy as np
    import wave
    import io
    
    sr = 24000
    duration = 5
    t = np.linspace(0, duration, sr * duration)
    audio = (np.sin(2 * np.pi * 440 * t) * 0.5 * 32767).astype(np.int16)
    
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(audio.tobytes())
    
    audio_bytes = buffer.getvalue()
    
    async def run():
        result = await audio_processor.preprocess_for_cloning(
            audio_bytes,
            target_duration=3.0,
            denoise=False  # 테스트용
        )
        assert result.duration > 0
        assert result.audio_bytes is not None
        print(f"✓ AudioProcessor OK (duration: {result.duration:.1f}s)")
    
    asyncio.run(run())


def test_speaker_diarizer_init():
    """SpeakerDiarizer 초기화 테스트"""
    from libs.audio import SpeakerDiarizer
    
    diarizer = SpeakerDiarizer()
    assert diarizer.hf_token is not None
    print("✓ SpeakerDiarizer init OK")


if __name__ == "__main__":
    print("=" * 50)
    print("Audio Library Tests")
    print("=" * 50)
    
    test_import()
    test_audio_processor()
    test_speaker_diarizer_init()
    
    print()
    print("All tests passed!")
