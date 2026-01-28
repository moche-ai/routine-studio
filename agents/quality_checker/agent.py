"""퀄리티 체커 에이전트 - 로컬/Gemini/Qwen 세 가지 버전"""
from agents.config import agent_settings

import sys
import json
import subprocess
import base64
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from PIL import Image
import numpy as np
import httpx

sys.path.insert(0, "/app")

from agents.base import BaseAgent, AgentResult, AgentStatus


class CheckerMode(Enum):
    LOCAL = "local"      # 로컬 분석 (Python 기반)
    GEMINI = "gemini"    # Google Gemini API 사용
    QWEN = "qwen"        # Qwen3-VL-30B Instruct (83% accuracy)


@dataclass
class QualityScore:
    """품질 점수 데이터"""
    overall: float
    details: Dict[str, float]
    issues: List[str]
    suggestions: List[str]
    summary: str


class LocalQualityChecker:
    """로컬 품질 체커 (Python/NumPy 기반)"""

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """이미지 품질 분석"""
        img = Image.open(image_path)
        arr = np.array(img)

        height, width = arr.shape[:2]
        mean_rgb = arr.mean(axis=(0, 1))[:3].astype(int)

        white_pixels = np.sum(np.all(arr > 240, axis=2))
        total_pixels = height * width
        white_ratio = white_pixels / total_pixels * 100

        black_pixels = np.sum(np.all(arr < 30, axis=2))
        black_ratio = black_pixels / total_pixels * 100

        color_std = arr.std()

        issues = []
        suggestions = []

        if white_ratio > 70:
            white_score = 2
            issues.append(f"흰색 비율이 너무 높음 ({white_ratio:.1f}%)")
            suggestions.append("캐릭터가 더 크게 그려져야 함")
        elif white_ratio > 50:
            white_score = 5
            issues.append(f"배경 비율이 높음 ({white_ratio:.1f}%)")
        elif white_ratio > 30:
            white_score = 7
        else:
            white_score = 9

        if black_ratio < 1:
            outline_score = 5
            issues.append("외곽선이 약함")
            suggestions.append("더 굵은 외곽선 추가 필요")
        elif black_ratio < 3:
            outline_score = 7
        else:
            outline_score = 9

        if color_std < 30:
            color_score = 4
            issues.append("색상이 단조로움")
        elif color_std < 50:
            color_score = 6
        else:
            color_score = 8

        if width < 512 or height < 512:
            resolution_score = 5
            issues.append(f"해상도가 낮음 ({width}x{height})")
        elif width >= 1024 and height >= 1024:
            resolution_score = 9
        else:
            resolution_score = 7

        overall = (white_score + outline_score + color_score + resolution_score) / 4

        return {
            "overall_score": round(overall, 1),
            "composition_score": round(white_score, 1),
            "color_quality": round(color_score, 1),
            "character_visibility": round(10 - white_ratio/10, 1),
            "background_cleanliness": round(min(10, white_ratio/5), 1),
            "style_consistency": round(outline_score, 1),
            "issues": issues,
            "suggestions": suggestions,
            "summary": f"전체 점수 {overall:.1f}/10, 흰색 {white_ratio:.1f}%, 외곽선 {black_ratio:.1f}%",
            "stats": {
                "resolution": f"{width}x{height}",
                "mean_rgb": tuple(mean_rgb),
                "white_ratio": round(white_ratio, 1),
                "black_ratio": round(black_ratio, 1),
                "color_std": round(color_std, 1)
            }
        }

    def analyze_video(self, video_path: str, num_frames: int = 5) -> Dict[str, Any]:
        """비디오 품질 분석 (픽셀 기반)"""
        path = Path(video_path)
        if not path.exists():
            return {"error": f"Video not found: {video_path}"}

        frame_results = []

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "ffmpeg", "-i", str(path),
                "-vf", f"select=not(mod(n\\,8))",
                "-vframes", str(num_frames),
                "-vsync", "vfr",
                f"{tmpdir}/frame_%03d.png"
            ]
            subprocess.run(cmd, capture_output=True)

            for frame_file in sorted(Path(tmpdir).glob("frame_*.png")):
                img = Image.open(frame_file)
                arr = np.array(img)

                mean_rgb = arr.mean(axis=(0, 1))[:3].astype(int)
                white_ratio = np.sum(np.all(arr > 240, axis=2)) / (arr.shape[0] * arr.shape[1]) * 100

                frame_results.append({
                    "mean_rgb": tuple(mean_rgb),
                    "white_ratio": round(white_ratio, 1)
                })

        if not frame_results:
            return {"error": "프레임 추출 실패"}

        white_ratios = [f["white_ratio"] for f in frame_results]
        rgb_values = [f["mean_rgb"] for f in frame_results]

        avg_white = np.mean(white_ratios)
        white_variance = np.std(white_ratios)

        rgb_changes = []
        for i in range(1, len(rgb_values)):
            change = np.sqrt(sum((a - b) ** 2 for a, b in zip(rgb_values[i], rgb_values[i-1])))
            rgb_changes.append(change)
        avg_rgb_change = np.mean(rgb_changes) if rgb_changes else 0

        issues = []
        suggestions = []

        if avg_white > 50:
            issues.append(f"평균 흰색 비율이 높음 ({avg_white:.1f}%)")
            suggestions.append("캐릭터 색상이 제대로 생성되지 않음")
            color_score = 3
        elif avg_white > 20:
            issues.append(f"흰색 비율이 다소 높음 ({avg_white:.1f}%)")
            color_score = 6
        else:
            color_score = 8

        if white_variance > 20:
            issues.append("프레임 간 일관성 부족")
            consistency_score = 4
        elif white_variance > 10:
            consistency_score = 6
        else:
            consistency_score = 8

        if avg_rgb_change < 5:
            issues.append("모션이 거의 없음 (정적인 영상)")
            motion_score = 5
        elif avg_rgb_change > 50:
            issues.append("모션이 너무 급격함")
            motion_score = 5
        else:
            motion_score = 8

        overall = (color_score + consistency_score + motion_score) / 3

        return {
            "overall_score": round(overall, 1),
            "motion_quality": round(motion_score, 1),
            "frame_consistency": round(consistency_score, 1),
            "character_preservation": round(10 - avg_white/10, 1),
            "color_stability": round(color_score, 1),
            "artifacts": round(10 - white_variance/5, 1),
            "issues": issues,
            "suggestions": suggestions,
            "summary": f"전체 점수 {overall:.1f}/10, 평균 흰색 {avg_white:.1f}%, RGB 변화량 {avg_rgb_change:.1f}",
            "frame_analysis": frame_results
        }


class QwenQualityChecker:
    """Qwen3-VL-30B Instruct 기반 품질 체커 (캐릭터 일관성 분석)"""

    def __init__(self, base_url: str = agent_settings.vision_api_url):
        self.base_url = base_url
        self.model = "qwen3-vl-30b-instruct"

    def _load_image_base64(self, path: str) -> str:
        """이미지를 base64로 인코딩"""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def _extract_frames(self, video_path: str, num_frames: int = 4) -> List[str]:
        """비디오에서 프레임 추출 후 경로 반환"""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run([
                "ffmpeg", "-i", video_path,
                "-vf", f"select=not(mod(n\\,10))",
                "-vframes", str(num_frames),
                "-vsync", "vfr",
                f"{tmpdir}/frame_%02d.png", "-y"
            ], capture_output=True)

            frames = sorted(Path(tmpdir).glob("frame_*.png"))
            result = []
            for i, f in enumerate(frames):
                dest = f"/tmp/qc_frame_{i:02d}.png"
                subprocess.run(["cp", str(f), dest])
                result.append(dest)
            return result

    def _extract_json(self, text: str) -> Optional[dict]:
        """응답에서 JSON 추출"""
        import re
        matches = re.findall(r'\{[^{}]+\}', text)
        for match in reversed(matches):
            try:
                return json.loads(match)
            except:
                continue
        return None

    async def check_character_consistency(
        self,
        reference_path: str,
        frame_paths: List[str],
        strict: bool = True
    ) -> Dict[str, Any]:
        """캐릭터 일관성 검사 (strict_v1 프롬프트 - 83% 정확도)"""

        content = []
        content.append({"type": "text", "text": "REFERENCE (original character):"})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{self._load_image_base64(reference_path)}"}
        })

        for i, fp in enumerate(frame_paths[:3]):
            content.append({"type": "text", "text": f"FRAME {i+1}:"})
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{self._load_image_base64(fp)}"}
            })

        if strict:
            content.append({"type": "text", "text": """
AI VIDEO QUALITY CHECK - Be STRICT!

This is AI-generated video. AI often FAILS to maintain character consistency.
Look for these COMMON AI FAILURES:

FAIL conditions (score 1-4):
- Face MORPHS or DISTORTS between frames
- Character looks like DIFFERENT PERSON in any frame
- Hair style/color CHANGES
- Body proportions CHANGE
- Skin color/tone CHANGES significantly
- Eyes/nose/mouth shapes CHANGE

PASS conditions (score 8-10):
- EXACT same character in ALL frames
- Face stays IDENTICAL (not just similar)
- No morphing or distortion

Be harsh. Most AI videos FAIL. Output JSON:
{"score": <1-10>, "verdict": "<PASS or FAIL>"}"""})
        else:
            content.append({"type": "text", "text": """
Check if video frames show the same character as reference.
Output JSON: {"score": <1-10>, "verdict": "<PASS or FAIL>"}"""})

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 200,
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload
                )
                result = response.json()

                if "choices" in result:
                    text = result["choices"][0]["message"]["content"]
                    parsed = self._extract_json(text)

                    if parsed:
                        return {
                            "success": True,
                            "score": parsed.get("score"),
                            "verdict": parsed.get("verdict"),
                            "overall_score": parsed.get("score"),
                            "raw_response": text[:300],
                            "issues": ["Character inconsistency detected"] if parsed.get("verdict") == "FAIL" else [],
                            "suggestions": ["Regenerate video with better prompts"] if parsed.get("verdict") == "FAIL" else [],
                            "summary": f"Score: {parsed.get('score')}/10, Verdict: {parsed.get('verdict')}"
                        }
                    return {"success": False, "error": "JSON parse failed", "raw_response": text[:300]}
                return {"success": False, "error": str(result)[:200]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def analyze_video(
        self,
        video_path: str,
        reference_path: str,
        num_frames: int = 4
    ) -> Dict[str, Any]:
        """비디오 품질 분석 (캐릭터 일관성 기반)"""
        frame_paths = self._extract_frames(video_path, num_frames)
        if not frame_paths:
            return {"error": "프레임 추출 실패", "success": False}

        return await self.check_character_consistency(reference_path, frame_paths)


class QualityCheckerAgent(BaseAgent):
    """퀄리티 체커 에이전트"""

    def __init__(self, mode: CheckerMode = CheckerMode.QWEN):
        super().__init__("QualityCheckerAgent")
        self.mode = mode
        self.local_checker = LocalQualityChecker()
        self.qwen_checker = QwenQualityChecker()
        self._gemini_service = None

    @property
    def gemini_service(self):
        """Gemini 서비스 지연 로딩"""
        if self._gemini_service is None:
            from apps.api.services.gemini import gemini_service
            self._gemini_service = gemini_service
        return self._gemini_service

    async def check_image(self, image_path: str) -> Dict[str, Any]:
        """이미지 품질 체크"""
        if self.mode == CheckerMode.LOCAL:
            return self.local_checker.analyze_image(image_path)
        elif self.mode == CheckerMode.QWEN:
            # Qwen은 이미지 단독 분석도 가능하지만 주로 비디오 QC에 사용
            return self.local_checker.analyze_image(image_path)
        else:
            return await self.gemini_service.quality_check_image(image_path)

    async def check_video(
        self,
        video_path: str,
        reference_path: str = None
    ) -> Dict[str, Any]:
        """비디오 품질 체크"""
        if self.mode == CheckerMode.LOCAL:
            return self.local_checker.analyze_video(video_path)
        elif self.mode == CheckerMode.QWEN:
            if not reference_path:
                # reference가 없으면 LOCAL 분석으로 폴백
                return self.local_checker.analyze_video(video_path)
            return await self.qwen_checker.analyze_video(video_path, reference_path)
        else:
            return await self.gemini_service.quality_check_video(video_path)

    async def check_batch(
        self,
        image_paths: List[str] = None,
        video_paths: List[str] = None,
        reference_path: str = None
    ) -> Dict[str, Any]:
        """배치 품질 체크"""
        results = {
            "images": [],
            "videos": [],
            "summary": {}
        }

        if image_paths:
            for path in image_paths:
                result = await self.check_image(path)
                result["path"] = path
                results["images"].append(result)

        if video_paths:
            for path in video_paths:
                result = await self.check_video(path, reference_path)
                result["path"] = path
                results["videos"].append(result)

        if results["images"]:
            scores = [r.get("overall_score", 0) for r in results["images"]]
            results["summary"]["avg_image_score"] = round(sum(scores) / len(scores), 1)
            results["summary"]["best_image"] = results["images"][scores.index(max(scores))]["path"]

        if results["videos"]:
            scores = [r.get("overall_score", 0) or r.get("score", 0) for r in results["videos"]]
            valid_scores = [s for s in scores if s]
            if valid_scores:
                results["summary"]["avg_video_score"] = round(sum(valid_scores) / len(valid_scores), 1)
                results["summary"]["best_video"] = results["videos"][scores.index(max(scores))]["path"]

            # PASS/FAIL 통계
            verdicts = [r.get("verdict") for r in results["videos"] if r.get("verdict")]
            if verdicts:
                results["summary"]["pass_count"] = verdicts.count("PASS")
                results["summary"]["fail_count"] = verdicts.count("FAIL")

        return results

    async def compare_with_gemini(
        self,
        image_paths: List[str] = None,
        video_paths: List[str] = None
    ) -> Dict[str, Any]:
        """Gemini를 사용한 고급 비교 분석"""
        return await self.gemini_service.compare_quality(image_paths, video_paths)

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """에이전트 실행"""
        self.status = AgentStatus.RUNNING

        image_paths = input_data.get("images", [])
        video_paths = input_data.get("videos", [])
        reference_path = input_data.get("reference")
        use_gemini = input_data.get("use_gemini", False)
        use_qwen = input_data.get("use_qwen", True)  # 기본값 Qwen

        if use_gemini:
            self.mode = CheckerMode.GEMINI
        elif use_qwen:
            self.mode = CheckerMode.QWEN

        try:
            results = await self.check_batch(image_paths, video_paths, reference_path)

            self.status = AgentStatus.COMPLETED
            return AgentResult(
                success=True,
                step="quality_check",
                message=self._format_results(results),
                needs_feedback=False,
                data=results
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(
                success=False,
                step="quality_check",
                message=f"품질 체크 실패: {e}",
                needs_feedback=False,
                data={"error": str(e)}
            )

    def _format_results(self, results: Dict[str, Any]) -> str:
        """결과 포맷팅"""
        lines = ["# 📊 품질 체크 결과\n"]

        if results.get("images"):
            lines.append("## 이미지 분석\n")
            for img in results["images"]:
                path = Path(img["path"]).name
                score = img.get("overall_score", "N/A")
                lines.append(f"- **{path}**: {score}/10")
                if img.get("issues"):
                    for issue in img["issues"][:2]:
                        lines.append(f"  - {issue}")
            lines.append("")

        if results.get("videos"):
            lines.append("## 비디오 분석\n")
            for vid in results["videos"]:
                path = Path(vid["path"]).name
                score = vid.get("overall_score") or vid.get("score", "N/A")
                verdict = vid.get("verdict", "")
                verdict_emoji = "" if verdict == "PASS" else "" if verdict == "FAIL" else ""
                lines.append(f"- **{path}**: {score}/10 {verdict_emoji} {verdict}")
                if vid.get("issues"):
                    for issue in vid["issues"][:2]:
                        lines.append(f"  - {issue}")
            lines.append("")

        if results.get("summary"):
            lines.append("## 요약\n")
            summary = results["summary"]
            if "avg_image_score" in summary:
                lines.append(f"- 평균 이미지 점수: {summary['avg_image_score']}/10")
            if "avg_video_score" in summary:
                lines.append(f"- 평균 비디오 점수: {summary['avg_video_score']}/10")
            if "pass_count" in summary:
                lines.append(f"- PASS: {summary['pass_count']}, FAIL: {summary['fail_count']}")
            if "best_image" in summary:
                lines.append(f"- 최고 이미지: {Path(summary['best_image']).name}")
            if "best_video" in summary:
                lines.append(f"- 최고 비디오: {Path(summary['best_video']).name}")

        return "\n".join(lines)
