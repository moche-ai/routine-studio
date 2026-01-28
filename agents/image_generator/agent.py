"""이미지/영상 생성 에이전트 - Qwen QC 통합 버전"""

import sys
import os
import json
import base64
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum

sys.path.append("/app")

from agents.base import BaseAgent, AgentResult, AgentStatus
from apps.api.services.comfyui import comfyui_service
from .workflows import get_first_image_workflow, get_consistent_image_workflow, get_wan_i2v_workflow


def emit_progress(status: str, detail: str = ""):
    """진행 상황 발생"""
    try:
        import builtins
        if hasattr(builtins, "emit_agent_progress"):
            builtins.emit_agent_progress(status, detail)
    except:
        pass


class GeneratorPhase(Enum):
    READY = "ready"
    GENERATING_IMAGES = "generating_images"
    GENERATING_VIDEOS = "generating_videos"
    QUALITY_CHECK = "quality_check"
    REVIEW = "review"
    DONE = "done"


# 출력 디렉토리
OUTPUT_DIR = Path("/app/output/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ImageGeneratorAgent(BaseAgent):
    """이미지/영상 생성 에이전트 (Qwen QC 통합)"""

    def __init__(self):
        super().__init__("ImageGeneratorAgent")
        self.phase = GeneratorPhase.READY
        self.prompts: List[Dict] = []
        self.generated_images: List[Dict] = []
        self.generated_videos: List[Dict] = []
        self.qc_results: List[Dict] = []
        self.reference_image_path: Optional[str] = None
        self.session_id: str = ""
        self.generate_videos: bool = True
        self.enable_qc: bool = True  # Qwen QC 활성화 여부
        self.max_regenerations: int = 2  # 최대 재생성 횟수
        self._qwen_checker = None

    @property
    def qwen_checker(self):
        """Qwen QC 지연 로딩"""
        if self._qwen_checker is None:
            from agents.quality_checker.agent import QwenQualityChecker
            self._qwen_checker = QwenQualityChecker()
        return self._qwen_checker

    def _save_image_from_base64(self, b64_data: str, filename: str) -> str:
        """Base64 이미지를 파일로 저장"""
        if "," in b64_data:
            b64_data = b64_data.split(",")[1]

        img_data = base64.b64decode(b64_data)
        file_path = OUTPUT_DIR / self.session_id / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(img_data)

        return str(file_path)

    async def _generate_first_image(self, prompt: Dict) -> Dict[str, Any]:
        """첫 번째 캐릭터 이미지 생성 (레퍼런스용)"""
        emit_progress("첫 캐릭터 이미지 생성 중", "레퍼런스 생성")

        image_prompt = prompt.get("image_prompt", "")

        workflow = get_first_image_workflow(
            prompt=image_prompt,
            checkpoint="CartoonXL.safetensors",
            width=1024,
            height=1024,
            steps=25,
            cfg=7.0
        )

        try:
            images = await comfyui_service.execute_workflow(workflow, timeout=180)

            if images:
                filename = f"scene_001_ref.png"
                saved_path = self._save_image_from_base64(images[0], filename)
                self.reference_image_path = saved_path

                input_path = f"/data/comfyui/input/routine_ref_{self.session_id}.png"
                import shutil
                shutil.copy(saved_path, input_path)

                return {
                    "line_num": prompt.get("line_num", 1),
                    "image_path": saved_path,
                    "image_b64": images[0],
                    "comfyui_input_path": f"routine_ref_{self.session_id}.png",
                    "success": True
                }
        except Exception as e:
            print(f"[ImageGenerator] First image error: {e}")
            return {
                "line_num": prompt.get("line_num", 1),
                "error": str(e),
                "success": False
            }

        return {"line_num": prompt.get("line_num", 1), "success": False, "error": "No image generated"}

    async def _generate_consistent_image(self, prompt: Dict, line_num: int) -> Dict[str, Any]:
        """IP-Adapter로 일관된 캐릭터 이미지 생성"""
        emit_progress(f"이미지 생성 중", f"{line_num}/{len(self.prompts)}")

        image_prompt = prompt.get("image_prompt", "")
        ref_filename = f"routine_ref_{self.session_id}.png"

        workflow = get_consistent_image_workflow(
            prompt=image_prompt,
            reference_image_path=ref_filename,
            checkpoint="CartoonXL.safetensors",
            ip_adapter_weight=0.7,
            width=1024,
            height=1024,
            steps=25,
            cfg=7.0
        )

        try:
            images = await comfyui_service.execute_workflow(workflow, timeout=180)

            if images:
                filename = f"scene_{line_num:03d}.png"
                saved_path = self._save_image_from_base64(images[0], filename)

                return {
                    "line_num": line_num,
                    "image_path": saved_path,
                    "image_b64": images[0],
                    "success": True
                }
        except Exception as e:
            print(f"[ImageGenerator] Image {line_num} error: {e}")
            return {
                "line_num": line_num,
                "error": str(e),
                "success": False
            }

        return {"line_num": line_num, "success": False, "error": "No image generated"}

    async def _generate_video(self, image_data: Dict, prompt: Dict) -> Dict[str, Any]:
        """이미지에서 영상 생성"""
        line_num = image_data.get("line_num", 1)
        emit_progress(f"영상 생성 중", f"{line_num}/{len(self.generated_images)}")

        image_path = image_data.get("image_path", "")
        video_prompt = prompt.get("video_prompt", "")

        if not image_path or not os.path.exists(image_path):
            return {
                "line_num": line_num,
                "error": "Image not found",
                "success": False
            }

        input_filename = f"routine_scene_{self.session_id}_{line_num:03d}.png"
        input_path = f"/data/comfyui/input/{input_filename}"
        import shutil
        shutil.copy(image_path, input_path)

        workflow = get_wan_i2v_workflow(
            image_path=input_filename,
            prompt=video_prompt,
            width=832,
            height=480,
            num_frames=81,
            steps=30,
            cfg=5.0
        )

        try:
            results = await comfyui_service.execute_workflow(workflow, timeout=600)

            if results:
                video_filename = f"scene_{line_num:03d}.mp4"
                saved_path = self._save_image_from_base64(results[0], video_filename)

                return {
                    "line_num": line_num,
                    "video_path": saved_path,
                    "video_b64": results[0],
                    "success": True
                }
        except Exception as e:
            print(f"[ImageGenerator] Video {line_num} error: {e}")
            return {
                "line_num": line_num,
                "error": str(e),
                "success": False
            }

        return {"line_num": line_num, "success": False, "error": "No video generated"}

    async def _run_quality_check(self, video_data: Dict, line_num: int) -> Dict[str, Any]:
        """Qwen으로 비디오 품질 검사"""
        if not self.enable_qc or not video_data.get("success"):
            return {"line_num": line_num, "skipped": True}

        emit_progress(f"품질 검사 중", f"{line_num}/{len(self.generated_videos)}")

        video_path = video_data.get("video_path", "")
        if not video_path or not os.path.exists(video_path):
            return {"line_num": line_num, "error": "Video not found"}

        try:
            result = await self.qwen_checker.analyze_video(
                video_path=video_path,
                reference_path=self.reference_image_path
            )

            result["line_num"] = line_num
            return result
        except Exception as e:
            print(f"[ImageGenerator] QC error for video {line_num}: {e}")
            return {"line_num": line_num, "error": str(e)}

    async def _generate_video_with_qc(
        self,
        image_data: Dict,
        prompt: Dict,
        regeneration_count: int = 0
    ) -> tuple:
        """영상 생성 + QC + 필요시 재생성"""
        line_num = image_data.get("line_num", 1)

        # 영상 생성
        video_result = await self._generate_video(image_data, prompt)

        if not video_result.get("success"):
            return video_result, {"line_num": line_num, "skipped": True}

        # QC 실행
        qc_result = await self._run_quality_check(video_result, line_num)

        # FAIL이고 재생성 횟수 남아있으면 재생성
        if (
            qc_result.get("verdict") == "FAIL" and
            regeneration_count < self.max_regenerations and
            self.enable_qc
        ):
            print(f"[ImageGenerator] Video {line_num} FAILED QC (attempt {regeneration_count + 1}), regenerating...")
            emit_progress(f"재생성 중", f"장면 {line_num} (QC 실패)")
            return await self._generate_video_with_qc(image_data, prompt, regeneration_count + 1)

        video_result["qc_verdict"] = qc_result.get("verdict", "N/A")
        video_result["qc_score"] = qc_result.get("score")
        video_result["regeneration_count"] = regeneration_count

        return video_result, qc_result

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """에이전트 시작"""
        self.status = AgentStatus.RUNNING
        self.phase = GeneratorPhase.READY

        self.session_id = input_data.get("session_id", "default")

        prompts = input_data.get("prompts", [])
        if not prompts:
            prompts = input_data.get("image_prompts", {}).get("prompts", [])

        if not prompts:
            self.status = AgentStatus.WAITING_FEEDBACK
            return AgentResult(
                success=True,
                step="image_generate",
                message="**이미지/영상 생성**\n\n프롬프트가 없습니다. 먼저 이미지 프롬프트를 생성해주세요.",
                needs_feedback=True,
                data={"phase": "ready"}
            )

        self.prompts = prompts
        self.generate_videos = input_data.get("generate_videos", True)
        self.enable_qc = input_data.get("enable_qc", True)

        return await self._start_generation()

    async def _start_generation(self) -> AgentResult:
        """이미지/영상 생성 시작"""
        self.phase = GeneratorPhase.GENERATING_IMAGES
        self.generated_images = []
        self.generated_videos = []
        self.qc_results = []

        total = len(self.prompts)
        emit_progress("이미지 생성 시작", f"총 {total}장")

        # 1. 첫 번째 이미지 생성 (레퍼런스)
        first_result = await self._generate_first_image(self.prompts[0])
        self.generated_images.append(first_result)

        if not first_result.get("success"):
            return AgentResult(
                success=False,
                step="image_generate",
                message=f"첫 번째 이미지 생성 실패: {first_result.get('error', 'Unknown error')}\n\nComfyUI가 실행 중인지 확인해주세요.",
                needs_feedback=True,
                data={"phase": "ready", "error": first_result.get("error")}
            )

        # 2. 나머지 이미지 생성 (IP-Adapter로 일관성 유지)
        for i, prompt in enumerate(self.prompts[1:], 2):
            result = await self._generate_consistent_image(prompt, i)
            self.generated_images.append(result)

            if not result.get("success"):
                print(f"[ImageGenerator] Scene {i} failed, continuing...")

        # 3. 영상 생성 + QC (옵션)
        if self.generate_videos:
            self.phase = GeneratorPhase.GENERATING_VIDEOS
            emit_progress("영상 생성 시작", f"총 {total}개")

            for i, (img_data, prompt) in enumerate(zip(self.generated_images, self.prompts), 1):
                if img_data.get("success"):
                    video_result, qc_result = await self._generate_video_with_qc(img_data, prompt)
                    self.generated_videos.append(video_result)
                    self.qc_results.append(qc_result)
                else:
                    self.generated_videos.append({
                        "line_num": i,
                        "success": False,
                        "error": "Source image failed"
                    })
                    self.qc_results.append({"line_num": i, "skipped": True})

        # 4. 결과 정리
        self.phase = GeneratorPhase.REVIEW
        result_text = self._format_results()

        self.status = AgentStatus.WAITING_FEEDBACK
        return AgentResult(
            success=True,
            step="image_generate_review",
            message=result_text,
            needs_feedback=True,
            data={
                "phase": "review",
                "images": self.generated_images,
                "videos": self.generated_videos,
                "qc_results": self.qc_results,
                "session_id": self.session_id
            }
        )

    def _format_results(self) -> str:
        """생성 결과 포맷팅"""
        lines = ["# 이미지/영상 생성 완료\n"]

        success_images = sum(1 for img in self.generated_images if img.get("success"))
        success_videos = sum(1 for vid in self.generated_videos if vid.get("success"))
        pass_count = sum(1 for qc in self.qc_results if qc.get("verdict") == "PASS")
        fail_count = sum(1 for qc in self.qc_results if qc.get("verdict") == "FAIL")

        lines.append(f"- 이미지: **{success_images}/{len(self.generated_images)}** 성공")
        if self.generate_videos:
            lines.append(f"- 영상: **{success_videos}/{len(self.generated_videos)}** 성공")
            if self.enable_qc and (pass_count + fail_count) > 0:
                lines.append(f"- 품질검사: **{pass_count}** PASS / **{fail_count}** FAIL")
        lines.append(f"- 저장 위치: `{OUTPUT_DIR / self.session_id}`")
        lines.append("\n---\n")

        for i, (img, prompt) in enumerate(zip(self.generated_images, self.prompts), 1):
            lines.append(f"### 장면 {i}")
            script_line = prompt.get('script_line', '')
            lines.append(f"**대본:** {script_line[:50]}..." if len(script_line) > 50 else f"**대본:** {script_line}")

            if img.get("success"):
                img_path = Path(img['image_path']).name
                lines.append(f"이미지: `{img_path}`")
            else:
                lines.append(f"이미지 실패: {img.get('error', 'Unknown')}")

            if self.generate_videos and i <= len(self.generated_videos):
                vid = self.generated_videos[i - 1]
                if vid.get("success"):
                    qc_status = ""
                    if self.enable_qc:
                        verdict = vid.get("qc_verdict", "N/A")
                        score = vid.get("qc_score", "?")
                        regen = vid.get("regeneration_count", 0)
                        emoji = "" if verdict == "PASS" else "" if verdict == "FAIL" else ""
                        qc_status = f" {emoji} QC:{verdict} ({score}/10)"
                        if regen > 0:
                            qc_status += f" (재생성 {regen}회)"
                    vid_path = Path(vid['video_path']).name
                    lines.append(f"영상: `{vid_path}`{qc_status}")
                else:
                    lines.append(f"영상 실패: {vid.get('error', 'Unknown')}")

            lines.append("")

        lines.append("---\n")
        lines.append("결과가 만족스러우면 **확인**을 입력해주세요.")
        lines.append("특정 장면을 다시 생성하려면 번호를 입력해주세요. (예: \"3번 다시\")")

        return "\n".join(lines)

    async def handle_feedback(self, feedback: str, images: List[str] = None) -> AgentResult:
        """피드백 처리"""
        feedback_lower = feedback.lower().strip()

        if self.phase == GeneratorPhase.REVIEW:
            if any(kw in feedback_lower for kw in ["확인", "완료", "ok", "좋아", "다음"]):
                self.phase = GeneratorPhase.DONE
                self.status = AgentStatus.COMPLETED

                return AgentResult(
                    success=True,
                    step="image_generate_done",
                    message="이미지/영상 생성이 완료되었습니다!\n\n다음 단계로 진행합니다.",
                    needs_feedback=False,
                    data={
                        "phase": "done",
                        "images": self.generated_images,
                        "videos": self.generated_videos,
                        "qc_results": self.qc_results,
                        "output_dir": str(OUTPUT_DIR / self.session_id)
                    }
                )

            import re
            match = re.search(r"(\d+)번?\s*(다시|재생성)?", feedback)
            if match:
                line_num = int(match.group(1))
                if 1 <= line_num <= len(self.prompts):
                    return await self._regenerate_scene(line_num)

        return AgentResult(
            success=True,
            step="image_generate_review",
            message="**확인**을 입력하거나, 다시 생성할 장면 번호를 입력해주세요.\n예: \"3번 다시\"",
            needs_feedback=True,
            data={"phase": self.phase.value}
        )

    async def _regenerate_scene(self, line_num: int) -> AgentResult:
        """특정 장면 다시 생성"""
        emit_progress(f"장면 {line_num} 재생성 중", "")

        prompt = self.prompts[line_num - 1]

        if line_num == 1:
            img_result = await self._generate_first_image(prompt)
        else:
            img_result = await self._generate_consistent_image(prompt, line_num)

        self.generated_images[line_num - 1] = img_result

        if self.generate_videos and img_result.get("success"):
            vid_result, qc_result = await self._generate_video_with_qc(img_result, prompt)
            if line_num - 1 < len(self.generated_videos):
                self.generated_videos[line_num - 1] = vid_result
                self.qc_results[line_num - 1] = qc_result
            else:
                self.generated_videos.append(vid_result)
                self.qc_results.append(qc_result)

        result_text = self._format_results()

        return AgentResult(
            success=True,
            step="image_generate_review",
            message=f"🔄 장면 {line_num}이 재생성되었습니다!\n\n{result_text}",
            needs_feedback=True,
            data={
                "phase": "review",
                "images": self.generated_images,
                "videos": self.generated_videos,
                "qc_results": self.qc_results,
                "regenerated_line": line_num
            }
        )
