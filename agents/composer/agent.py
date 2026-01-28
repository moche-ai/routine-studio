"""Composer Agent - 영상, 음성, 자막을 하나로 합성"""

import sys
import os
import json
import subprocess
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum
from dataclasses import dataclass

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


class ComposerPhase(Enum):
    READY = "ready"
    ANALYZING = "analyzing"
    SYNCING = "syncing"
    COMPOSING = "composing"
    REVIEW = "review"
    DONE = "done"


@dataclass
class SceneData:
    """장면 데이터"""
    index: int
    script_line: str
    image_path: str
    video_path: str
    audio_path: str
    audio_duration: float  # 초 단위
    start_time: float  # 전체 영상에서 시작 시간
    end_time: float


OUTPUT_DIR = Path("/app/output/images")


class ComposerAgent(BaseAgent):
    """영상 합성 에이전트 - 비디오 + 오디오 + 자막 싱크"""

    def __init__(self):
        super().__init__("ComposerAgent")
        self.phase = ComposerPhase.READY
        self.scenes: List[SceneData] = []
        self.session_id: str = ""
        self.output_dir: Path = OUTPUT_DIR
        self.final_video_path: str = ""
        self.subtitle_path: str = ""

    def _get_audio_duration(self, audio_path: str) -> float:
        """ffprobe로 오디오 길이 측정"""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"[Composer] Audio duration error: {e}")
            return 3.0  # 기본값 3초

    def _get_video_duration(self, video_path: str) -> float:
        """ffprobe로 비디오 길이 측정"""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"[Composer] Video duration error: {e}")
            return 3.4  # 기본값

    def _adjust_video_duration(self, video_path: str, target_duration: float, output_path: str) -> bool:
        """비디오 길이를 오디오에 맞게 조절"""
        try:
            video_duration = self._get_video_duration(video_path)

            if abs(video_duration - target_duration) < 0.1:
                # 차이가 0.1초 미만이면 그냥 복사
                subprocess.run(["cp", video_path, output_path], check=True)
                return True

            if target_duration < video_duration:
                # 오디오가 더 짧음: 비디오 트림
                cmd = [
                    "ffmpeg", "-y", "-i", video_path,
                    "-t", str(target_duration),
                    "-c:v", "libx264", "-crf", "18",
                    output_path
                ]
            else:
                # 오디오가 더 김: 비디오 속도 조절 (최대 20% 느리게)
                speed_factor = video_duration / target_duration
                if speed_factor < 0.8:
                    # 너무 많이 늘려야 하면 마지막 프레임 홀드
                    cmd = [
                        "ffmpeg", "-y", "-i", video_path,
                        "-vf", f"tpad=stop_mode=clone:stop_duration={target_duration - video_duration}",
                        "-c:v", "libx264", "-crf", "18",
                        output_path
                    ]
                else:
                    # 적당히 늘릴 수 있으면 속도 조절
                    cmd = [
                        "ffmpeg", "-y", "-i", video_path,
                        "-vf", f"setpts={1/speed_factor}*PTS",
                        "-c:v", "libx264", "-crf", "18",
                        output_path
                    ]

            subprocess.run(cmd, capture_output=True, check=True)
            return True
        except Exception as e:
            print(f"[Composer] Video adjust error: {e}")
            return False

    def _generate_srt(self, scenes: List[SceneData], output_path: str) -> bool:
        """SRT 자막 파일 생성"""
        try:
            lines = []
            for i, scene in enumerate(scenes, 1):
                start = self._format_srt_time(scene.start_time)
                end = self._format_srt_time(scene.end_time)
                text = scene.script_line

                lines.append(f"{i}")
                lines.append(f"{start} --> {end}")
                lines.append(text)
                lines.append("")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            return True
        except Exception as e:
            print(f"[Composer] SRT generation error: {e}")
            return False

    def _format_srt_time(self, seconds: float) -> str:
        """초를 SRT 시간 형식으로 변환 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _concat_videos(self, video_paths: List[str], output_path: str) -> bool:
        """여러 비디오를 하나로 연결"""
        try:
            # concat demuxer용 파일 리스트 생성
            list_file = output_path + ".txt"
            with open(list_file, "w") as f:
                for vp in video_paths:
                    f.write(f"file '{vp}'\n")

            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file,
                "-c:v", "libx264", "-crf", "18",
                output_path
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            os.remove(list_file)
            return True
        except Exception as e:
            print(f"[Composer] Video concat error: {e}")
            return False

    def _concat_audios(self, audio_paths: List[str], output_path: str) -> bool:
        """여러 오디오를 하나로 연결"""
        try:
            # 필터 복합체로 연결
            filter_parts = []
            for i in range(len(audio_paths)):
                filter_parts.append(f"[{i}:a]")
            filter_str = "".join(filter_parts) + f"concat=n={len(audio_paths)}:v=0:a=1[out]"

            cmd = ["ffmpeg", "-y"]
            for ap in audio_paths:
                cmd.extend(["-i", ap])
            cmd.extend([
                "-filter_complex", filter_str,
                "-map", "[out]",
                output_path
            ])
            subprocess.run(cmd, capture_output=True, check=True)
            return True
        except Exception as e:
            print(f"[Composer] Audio concat error: {e}")
            return False

    def _merge_video_audio_subtitle(
        self,
        video_path: str,
        audio_path: str,
        subtitle_path: str,
        output_path: str,
        burn_subtitles: bool = True
    ) -> bool:
        """비디오 + 오디오 + 자막 합성"""
        try:
            if burn_subtitles:
                # 자막을 비디오에 굽기
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", audio_path,
                    "-vf", f"subtitles={subtitle_path}:force_style='FontSize=24,FontName=NanumGothic,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1'",
                    "-c:v", "libx264", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    output_path
                ]
            else:
                # 자막을 스트림으로 추가 (별도 트랙)
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", audio_path,
                    "-i", subtitle_path,
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-c:s", "mov_text",
                    "-shortest",
                    output_path
                ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[Composer] FFmpeg error: {result.stderr}")
                return False
            return True
        except Exception as e:
            print(f"[Composer] Merge error: {e}")
            return False

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """합성 시작"""
        self.status = AgentStatus.RUNNING
        self.phase = ComposerPhase.ANALYZING

        self.session_id = input_data.get("session_id", "default")
        self.output_dir = OUTPUT_DIR / self.session_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 입력 데이터 수집
        videos = input_data.get("videos", [])
        audios = input_data.get("audios", [])
        prompts = input_data.get("prompts", [])

        if not videos or not audios:
            return AgentResult(
                success=False,
                step="compose",
                message="비디오 또는 오디오 데이터가 없습니다.",
                needs_feedback=False,
                data={"error": "Missing video or audio data"}
            )

        emit_progress("합성 준비", f"비디오 {len(videos)}개, 오디오 {len(audios)}개")

        # 장면 데이터 구성
        self.scenes = []
        current_time = 0.0

        for i, (video, audio) in enumerate(zip(videos, audios)):
            video_path = video.get("video_path", "")
            audio_path = audio.get("filepath", "") or audio.get("audio_path", "")
            script_line = prompts[i].get("script_line", "") if i < len(prompts) else ""

            if not video_path or not audio_path:
                continue

            if not os.path.exists(video_path) or not os.path.exists(audio_path):
                print(f"[Composer] Scene {i+1}: File not found")
                continue

            audio_duration = self._get_audio_duration(audio_path)

            scene = SceneData(
                index=i + 1,
                script_line=script_line,
                image_path=video.get("image_path", ""),
                video_path=video_path,
                audio_path=audio_path,
                audio_duration=audio_duration,
                start_time=current_time,
                end_time=current_time + audio_duration
            )
            self.scenes.append(scene)
            current_time += audio_duration

        if not self.scenes:
            return AgentResult(
                success=False,
                step="compose",
                message="유효한 장면이 없습니다.",
                needs_feedback=False,
                data={"error": "No valid scenes"}
            )

        # 합성 시작
        return await self._compose_all()

    async def _compose_all(self) -> AgentResult:
        """전체 합성 프로세스"""
        self.phase = ComposerPhase.SYNCING

        # 1. 각 비디오를 오디오 길이에 맞게 조절
        emit_progress("비디오 싱크", f"총 {len(self.scenes)}개 장면")

        adjusted_videos = []
        for scene in self.scenes:
            emit_progress("비디오 조절", f"장면 {scene.index}")

            adjusted_path = str(self.output_dir / f"adjusted_{scene.index:03d}.mp4")
            success = self._adjust_video_duration(
                scene.video_path,
                scene.audio_duration,
                adjusted_path
            )

            if success:
                adjusted_videos.append(adjusted_path)
            else:
                # 실패시 원본 사용
                adjusted_videos.append(scene.video_path)

        # 2. SRT 자막 생성
        emit_progress("자막 생성", "SRT 파일 생성 중")
        self.subtitle_path = str(self.output_dir / "subtitles.srt")
        self._generate_srt(self.scenes, self.subtitle_path)

        # 3. 비디오 연결
        self.phase = ComposerPhase.COMPOSING
        emit_progress("비디오 합성", "비디오 연결 중")

        concat_video_path = str(self.output_dir / "concat_video.mp4")
        self._concat_videos(adjusted_videos, concat_video_path)

        # 4. 오디오 연결
        emit_progress("오디오 합성", "오디오 연결 중")

        audio_paths = [s.audio_path for s in self.scenes]
        concat_audio_path = str(self.output_dir / "concat_audio.wav")
        self._concat_audios(audio_paths, concat_audio_path)

        # 5. 최종 합성 (비디오 + 오디오 + 자막)
        emit_progress("최종 합성", "비디오+오디오+자막 합성 중")

        self.final_video_path = str(self.output_dir / f"final_{self.session_id}.mp4")
        success = self._merge_video_audio_subtitle(
            concat_video_path,
            concat_audio_path,
            self.subtitle_path,
            self.final_video_path,
            burn_subtitles=True
        )

        # 임시 파일 정리
        for vp in adjusted_videos:
            if "adjusted_" in vp and os.path.exists(vp):
                os.remove(vp)
        if os.path.exists(concat_video_path):
            os.remove(concat_video_path)
        if os.path.exists(concat_audio_path):
            os.remove(concat_audio_path)

        if not success:
            return AgentResult(
                success=False,
                step="compose",
                message="최종 합성에 실패했습니다.",
                needs_feedback=True,
                data={"error": "Final merge failed"}
            )

        # 6. 결과 정리
        self.phase = ComposerPhase.REVIEW
        total_duration = sum(s.audio_duration for s in self.scenes)

        result_text = f"""# 영상 합성 완료

**총 길이:** {total_duration:.1f}초 ({len(self.scenes)}개 장면)

**출력 파일:**
- 최종 영상: `{Path(self.final_video_path).name}`
- 자막 파일: `{Path(self.subtitle_path).name}`
- 저장 위치: `{self.output_dir}`

**장면 구성:**
"""
        for scene in self.scenes:
            result_text += f"- 장면 {scene.index}: {scene.audio_duration:.1f}초 ({scene.start_time:.1f}s ~ {scene.end_time:.1f}s)\n"
            result_text += f"  \"{scene.script_line[:30]}...\"\n"

        result_text += "\n확인을 입력하면 완료됩니다."

        self.status = AgentStatus.WAITING_FEEDBACK
        return AgentResult(
            success=True,
            step="compose_review",
            message=result_text,
            needs_feedback=True,
            data={
                "phase": "review",
                "final_video": self.final_video_path,
                "subtitle_file": self.subtitle_path,
                "total_duration": total_duration,
                "scenes": [
                    {
                        "index": s.index,
                        "script_line": s.script_line,
                        "duration": s.audio_duration,
                        "start_time": s.start_time,
                        "end_time": s.end_time
                    }
                    for s in self.scenes
                ]
            }
        )

    async def handle_feedback(self, feedback: str, images: List[str] = None) -> AgentResult:
        """피드백 처리"""
        feedback_lower = feedback.lower().strip()

        if self.phase == ComposerPhase.REVIEW:
            if any(kw in feedback_lower for kw in ["확인", "완료", "ok", "좋아", "다음"]):
                self.phase = ComposerPhase.DONE
                self.status = AgentStatus.COMPLETED

                return AgentResult(
                    success=True,
                    step="compose_done",
                    message=f"영상 합성이 완료되었습니다!\n\n최종 파일: `{self.final_video_path}`",
                    needs_feedback=False,
                    data={
                        "phase": "done",
                        "final_video": self.final_video_path,
                        "subtitle_file": self.subtitle_path
                    }
                )

        return AgentResult(
            success=True,
            step="compose_review",
            message="확인을 입력하면 완료됩니다.",
            needs_feedback=True,
            data={"phase": self.phase.value}
        )
