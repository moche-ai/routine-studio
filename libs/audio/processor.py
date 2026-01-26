"""
오디오 전처리 모듈 v2

음성/비음성 구분 강화 + 노이즈 제거 + 최적 구간 추출

Qwen3-TTS 권장사항:
- 최소 3초, 권장 3-15초
- 1.7B 모델은 노이즈에 강건하지만 깨끗한 오디오가 더 좋음
- ref_text가 정확해야 품질 향상
"""

import asyncio
import io
import os
import tempfile
import wave
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np


@dataclass
class AudioSegment:
    """오디오 세그먼트 정보"""
    start_sec: float
    end_sec: float
    duration: float
    energy: float
    zcr: float  # Zero-crossing rate
    spectral_centroid: float
    voice_band_ratio: float
    voice_score: float  # 종합 음성 점수 (0~1)
    is_voice: bool


@dataclass
class ProcessedAudio:
    """전처리된 오디오 결과"""
    audio_bytes: bytes
    sample_rate: int
    duration: float
    original_duration: float
    segments_analyzed: int
    selected_range: Tuple[float, float]
    quality_score: float
    noise_reduced: bool = False


class AudioProcessor:
    """
    음성 복제를 위한 스마트 오디오 전처리

    기능:
    1. 음성/음악/노이즈 구분 (spectral 분석)
    2. ffmpeg afftdn 노이즈 제거 (선택적)
    3. 깔끔한 음성 구간만 3-7초로 추출
    """

    # 구간 길이 설정
    MIN_DURATION = 3.0      # 최소 3초
    OPTIMAL_MIN = 5.0       # 이상적 최소
    OPTIMAL_MAX = 7.0       # 이상적 최대
    ABSOLUTE_MAX = 10.0     # 절대 최대

    # 분석 프레임
    FRAME_DURATION = 0.03  # 30ms

    # 음성 판별 임계값
    ENERGY_THRESHOLD = 0.015
    VOICE_SCORE_THRESHOLD = 0.45

    # 음성 주파수 대역 (Hz)
    VOICE_FREQ_LOW = 85
    VOICE_FREQ_HIGH = 3400

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    async def _run_ffmpeg(self, args: List[str]) -> Tuple[bytes, bytes]:
        """ffmpeg 명령 실행"""
        cmd = [self.ffmpeg_path] + args
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        return await process.communicate()

    def _read_wav(self, audio_bytes: bytes) -> Tuple[np.ndarray, int]:
        """WAV 바이트를 numpy 배열로 변환"""
        with io.BytesIO(audio_bytes) as f:
            with wave.open(f, 'rb') as wav:
                sample_rate = wav.getframerate()
                n_channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                n_frames = wav.getnframes()

                raw_data = wav.readframes(n_frames)

                if sample_width == 1:
                    dtype = np.uint8
                elif sample_width == 2:
                    dtype = np.int16
                elif sample_width == 4:
                    dtype = np.int32
                else:
                    dtype = np.int16

                audio = np.frombuffer(raw_data, dtype=dtype)

                if n_channels == 2:
                    audio = audio.reshape(-1, 2).mean(axis=1)

                audio = audio.astype(np.float32)
                if dtype == np.uint8:
                    audio = (audio - 128) / 128
                else:
                    audio = audio / np.iinfo(dtype).max

                return audio, sample_rate

    def _write_wav(self, audio: np.ndarray, sample_rate: int) -> bytes:
        """numpy 배열을 WAV 바이트로 변환"""
        audio_int16 = (audio * 32767).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio_int16.tobytes())

        return buffer.getvalue()

    async def reduce_noise(self, audio_bytes: bytes, strength: float = 0.5) -> bytes:
        """
        ffmpeg afftdn 필터로 노이즈 제거

        Args:
            audio_bytes: WAV 오디오
            strength: 노이즈 제거 강도 (0.0~1.0, 높을수록 강함)

        Returns:
            노이즈 제거된 WAV
        """
        # 노이즈 제거 강도를 dB로 변환 (5~25dB)
        noise_floor = int(5 + strength * 20)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_in:
            tmp_in.write(audio_bytes)
            input_path = tmp_in.name

        output_path = input_path.replace(".wav", "_denoised.wav")

        try:
            # afftdn: Adaptive FFT Denoiser
            await self._run_ffmpeg([
                "-i", input_path,
                "-af", f"afftdn=nf=-{noise_floor}:nr={noise_floor}:tn=1",
                "-y",
                output_path
            ])

            if os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    return f.read()
            return audio_bytes

        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)

    def _calculate_zcr(self, frame: np.ndarray) -> float:
        """Zero-crossing rate"""
        signs = np.sign(frame)
        signs[signs == 0] = 1
        crossings = np.sum(np.abs(np.diff(signs)) > 0)
        return crossings / len(frame)

    def _calculate_spectral_centroid(self, frame: np.ndarray, sample_rate: int) -> float:
        """스펙트럼 중심 주파수"""
        fft = np.abs(np.fft.rfft(frame))
        freqs = np.fft.rfftfreq(len(frame), 1/sample_rate)

        if np.sum(fft) < 1e-10:
            return 0

        return np.sum(freqs * fft) / np.sum(fft)

    def _calculate_voice_band_ratio(self, frame: np.ndarray, sample_rate: int) -> float:
        """음성 주파수 대역 에너지 비율"""
        fft = np.abs(np.fft.rfft(frame))
        freqs = np.fft.rfftfreq(len(frame), 1/sample_rate)

        total_energy = np.sum(fft ** 2)
        if total_energy < 1e-10:
            return 0

        voice_mask = (freqs >= self.VOICE_FREQ_LOW) & (freqs <= self.VOICE_FREQ_HIGH)
        voice_energy = np.sum(fft[voice_mask] ** 2)

        return voice_energy / total_energy

    def _calculate_spectral_flatness(self, frame: np.ndarray) -> float:
        """
        Spectral flatness (톤성 지표)
        - 낮으면 톤이 있음 (음성, 악기)
        - 높으면 노이즈에 가까움
        """
        fft = np.abs(np.fft.rfft(frame))
        fft = fft[fft > 1e-10]

        if len(fft) == 0:
            return 1.0

        geometric_mean = np.exp(np.mean(np.log(fft)))
        arithmetic_mean = np.mean(fft)

        if arithmetic_mean < 1e-10:
            return 1.0

        return geometric_mean / arithmetic_mean

    def _calculate_voice_score(
        self,
        energy: float,
        zcr: float,
        spectral_centroid: float,
        voice_band_ratio: float,
        spectral_flatness: float
    ) -> float:
        """
        종합 음성 점수 (0~1)

        음성 특성:
        - 적당한 에너지 (음악보다 낮고, 무음보다 높음)
        - ZCR 0.02~0.15
        - Spectral centroid 200~2500Hz
        - 높은 voice band ratio
        - 낮은 spectral flatness (톤이 있음)
        """
        scores = []

        # 1. 에너지 점수 (20%)
        if energy < self.ENERGY_THRESHOLD:
            energy_score = 0
        elif energy < 0.08:
            energy_score = min(1.0, energy / 0.04)
        elif energy < 0.25:
            energy_score = 1.0
        else:
            # 너무 높으면 음악일 가능성
            energy_score = max(0.2, 1.0 - (energy - 0.25) / 0.5)
        scores.append(energy_score * 0.15)

        # 2. ZCR 점수 (15%)
        if 0.02 <= zcr <= 0.15:
            zcr_score = 1.0
        elif zcr < 0.02:
            zcr_score = zcr / 0.02
        else:
            zcr_score = max(0, 1.0 - (zcr - 0.15) / 0.3)
        scores.append(zcr_score * 0.15)

        # 3. Spectral centroid 점수 (25%)
        if 200 <= spectral_centroid <= 2500:
            centroid_score = 1.0
        elif spectral_centroid < 200:
            centroid_score = spectral_centroid / 200
        elif spectral_centroid <= 5000:
            centroid_score = max(0.1, 1.0 - (spectral_centroid - 2500) / 5000)
        else:
            centroid_score = 0.05
        scores.append(centroid_score * 0.25)

        # 4. Voice band ratio 점수 (25%)
        voice_ratio_score = min(1.0, voice_band_ratio * 1.3)
        scores.append(voice_ratio_score * 0.25)

        # 5. Spectral flatness 점수 (20%) - 낮을수록 좋음
        if spectral_flatness < 0.1:
            flatness_score = 1.0
        elif spectral_flatness < 0.3:
            flatness_score = 1.0 - (spectral_flatness - 0.1) / 0.4
        else:
            flatness_score = max(0.1, 0.5 - spectral_flatness)
        scores.append(flatness_score * 0.20)

        return sum(scores)

    def _analyze_frames(self, audio: np.ndarray, sample_rate: int) -> List[AudioSegment]:
        """프레임별 분석"""
        frame_size = int(sample_rate * self.FRAME_DURATION)
        segments = []

        for i in range(0, len(audio) - frame_size, frame_size):
            frame = audio[i:i + frame_size]

            energy = np.sqrt(np.mean(frame ** 2))
            zcr = self._calculate_zcr(frame)
            spectral_centroid = self._calculate_spectral_centroid(frame, sample_rate)
            voice_band_ratio = self._calculate_voice_band_ratio(frame, sample_rate)
            spectral_flatness = self._calculate_spectral_flatness(frame)

            voice_score = self._calculate_voice_score(
                energy, zcr, spectral_centroid, voice_band_ratio, spectral_flatness
            )

            start_sec = i / sample_rate
            end_sec = (i + frame_size) / sample_rate
            is_voice = voice_score >= self.VOICE_SCORE_THRESHOLD

            segments.append(AudioSegment(
                start_sec=start_sec,
                end_sec=end_sec,
                duration=self.FRAME_DURATION,
                energy=energy,
                zcr=zcr,
                spectral_centroid=spectral_centroid,
                voice_band_ratio=voice_band_ratio,
                voice_score=voice_score,
                is_voice=is_voice
            ))

        return segments

    def _find_voice_regions(
        self,
        segments: List[AudioSegment],
        min_duration: float = 0.3,
        max_gap: float = 0.4  # 말 사이 쉬는 구간 허용
    ) -> List[Tuple[float, float, float]]:
        """연속된 음성 구간 찾기"""
        if not segments:
            return []

        regions = []
        current_start = None
        current_scores = []
        gap_count = 0
        max_gap_frames = int(max_gap / self.FRAME_DURATION)

        for seg in segments:
            if seg.is_voice:
                if current_start is None:
                    current_start = seg.start_sec
                current_scores.append(seg.voice_score)
                gap_count = 0
            else:
                if current_start is not None:
                    gap_count += 1
                    if gap_count > max_gap_frames:
                        end_sec = seg.start_sec - (gap_count * self.FRAME_DURATION)
                        duration = end_sec - current_start
                        if duration >= min_duration:
                            avg_score = np.mean(current_scores)
                            regions.append((current_start, end_sec, avg_score))
                        current_start = None
                        current_scores = []
                        gap_count = 0

        # 마지막 구간
        if current_start is not None and segments:
            end_sec = segments[-1].end_sec
            duration = end_sec - current_start
            if duration >= min_duration:
                avg_score = np.mean(current_scores)
                regions.append((current_start, end_sec, avg_score))

        return regions

    def _select_best_voice_segment(
        self,
        regions: List[Tuple[float, float, float]],
        total_duration: float,
        min_duration: float = 3.0,
        max_duration: float = 7.0
    ) -> Tuple[Tuple[float, float], float]:
        """최적의 음성 구간 선택 (품질 * 길이 최적화)"""
        if not regions:
            end = min(min_duration, total_duration)
            return ((0, end), 0.1)

        candidates = []

        for start, end, score in regions:
            duration = end - start

            if duration >= min_duration:
                if duration <= max_duration:
                    # 이상적 길이 - 길수록 약간 보너스
                    length_factor = 0.9 + 0.1 * (duration / max_duration)
                    quality = score * length_factor
                    candidates.append(((start, end), quality, duration))
                else:
                    # 너무 김 - max_duration만큼 자르기
                    quality = score * 0.85
                    candidates.append(((start, start + max_duration), quality, max_duration))

            elif duration >= 2.0:
                # 약간 짧지만 품질 좋으면 사용
                quality = score * 0.6 * (duration / min_duration)
                candidates.append(((start, end), quality, duration))

        if not candidates:
            best = max(regions, key=lambda r: (r[1] - r[0]) * r[2])
            start, end, score = best
            duration = min(end - start, max_duration)
            return ((start, start + duration), score * 0.4)

        # 품질 + 길이 보너스로 랭킹
        def rank(c):
            (s, e), quality, dur = c
            # 5-7초가 이상적
            if 5.0 <= dur <= 7.0:
                bonus = 0.15
            elif 4.0 <= dur < 5.0:
                bonus = 0.10
            elif 3.0 <= dur < 4.0:
                bonus = 0.05
            else:
                bonus = 0
            return quality + bonus

        best = max(candidates, key=rank)
        return (best[0], best[1])

    def _normalize_audio(self, audio: np.ndarray, target_db: float = -3.0) -> np.ndarray:
        """오디오 정규화"""
        peak = np.max(np.abs(audio))
        if peak < 1e-6:
            return audio

        target_peak = 10 ** (target_db / 20)
        return audio * (target_peak / peak)

    async def preprocess_for_cloning(
        self,
        audio_bytes: bytes,
        target_duration: float = None,
        normalize: bool = True,
        denoise: bool = True,
        denoise_strength: float = 0.4
    ) -> ProcessedAudio:
        """
        음성 복제를 위한 스마트 전처리

        1. 노이즈 제거 (선택적)
        2. 음성/음악/노이즈 구분 (spectral 분석)
        3. 깔끔한 음성 구간 3-7초 추출

        Args:
            audio_bytes: 입력 WAV
            target_duration: 목표 길이 (None이면 자동)
            normalize: 볼륨 정규화
            denoise: 노이즈 제거 여부
            denoise_strength: 노이즈 제거 강도 (0.0~1.0)

        Returns:
            ProcessedAudio
        """
        noise_reduced = False

        # 노이즈 제거
        if denoise:
            try:
                audio_bytes = await self.reduce_noise(audio_bytes, denoise_strength)
                noise_reduced = True
            except Exception:
                pass  # 실패해도 계속 진행

        min_dur = self.MIN_DURATION
        max_dur = self.OPTIMAL_MAX if target_duration is None else min(target_duration, self.ABSOLUTE_MAX)

        audio, sample_rate = self._read_wav(audio_bytes)
        original_duration = len(audio) / sample_rate

        # 짧은 오디오는 그대로
        if original_duration <= min_dur:
            if normalize:
                audio = self._normalize_audio(audio)
            return ProcessedAudio(
                audio_bytes=self._write_wav(audio, sample_rate),
                sample_rate=sample_rate,
                duration=original_duration,
                original_duration=original_duration,
                segments_analyzed=0,
                selected_range=(0, original_duration),
                quality_score=0.5,
                noise_reduced=noise_reduced
            )

        # 프레임별 분석
        segments = self._analyze_frames(audio, sample_rate)

        # 음성 구간 찾기
        voice_regions = self._find_voice_regions(segments)

        # 최적 구간 선택
        (start_sec, end_sec), quality_score = self._select_best_voice_segment(
            voice_regions,
            original_duration,
            min_duration=min_dur,
            max_duration=max_dur
        )

        # 추출
        start_sample = int(start_sec * sample_rate)
        end_sample = int(end_sec * sample_rate)
        extracted = audio[start_sample:end_sample]

        # 정규화
        if normalize:
            extracted = self._normalize_audio(extracted)

        duration = len(extracted) / sample_rate

        return ProcessedAudio(
            audio_bytes=self._write_wav(extracted, sample_rate),
            sample_rate=sample_rate,
            duration=duration,
            original_duration=original_duration,
            segments_analyzed=len(segments),
            selected_range=(start_sec, end_sec),
            quality_score=quality_score,
            noise_reduced=noise_reduced
        )

    async def auto_trim(
        self,
        audio_bytes: bytes,
        min_duration: float = 3.0,
        max_duration: float = 7.0
    ) -> ProcessedAudio:
        """자동 트리밍 (노이즈 제거 포함)"""
        return await self.preprocess_for_cloning(
            audio_bytes,
            target_duration=max_duration,
            normalize=True,
            denoise=True
        )

    async def convert_to_wav_24k(self, audio_bytes: bytes) -> bytes:
        """24kHz WAV로 변환 (Qwen3-TTS 권장)"""
        with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as tmp_in:
            tmp_in.write(audio_bytes)
            input_path = tmp_in.name

        output_path = input_path + ".wav"

        try:
            await self._run_ffmpeg([
                "-i", input_path,
                "-ar", "24000",
                "-ac", "1",
                "-y",
                output_path
            ])

            with open(output_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)


# 싱글톤 인스턴스
audio_processor = AudioProcessor()
