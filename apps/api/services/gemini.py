"""Google Gemini API 서비스 - 이미지/영상 분석 및 생성용"""

import os
import json
import subprocess
import tempfile
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from PIL import Image

# 환경변수에서 API 키 로드
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDWMMQPoQNTnSS0EwGVYJSNPUaM-PBK1UA")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "vertex-ai-test-485604")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
GCP_KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/data/gcp-key.json")


class GeminiService:
    """Google Gemini API 서비스"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash"
        self._vertex_client = None

    def _get_vertex_client(self):
        """Vertex AI 클라이언트 (lazy init)"""
        if self._vertex_client is None:
            import vertexai
            from vertexai.preview.vision_models import ImageGenerationModel

            # GCP 인증 설정
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_KEY_PATH

            # Vertex AI 초기화
            vertexai.init(project="vertex-ai-test-485604", location=GCP_LOCATION)
            self._vertex_client = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        return self._vertex_client

    def _extract_video_frames(self, video_path: str, num_frames: int = 5) -> List[Image.Image]:
        """비디오에서 프레임 추출"""
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        frames = []
        with tempfile.TemporaryDirectory() as tmpdir:
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-count_packets",
                "-show_entries", "stream=nb_read_packets",
                "-of", "csv=p=0",
                str(path)
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            total_frames = int(result.stdout.strip() or 41)

            interval = max(1, total_frames // num_frames)

            cmd = [
                "ffmpeg", "-i", str(path),
                "-vf", f"select=not(mod(n\\,{interval}))",
                "-vframes", str(num_frames),
                "-vsync", "vfr",
                f"{tmpdir}/frame_%03d.png"
            ]
            subprocess.run(cmd, capture_output=True)

            for frame_file in sorted(Path(tmpdir).glob("frame_*.png")):
                frames.append(Image.open(frame_file).copy())

        return frames

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        negative_prompt: str = None,
        aspect_ratio: str = "1:1",
        num_images: int = 1,
    ) -> List[str]:
        """Vertex AI Imagen으로 이미지 생성"""
        try:
            model = self._get_vertex_client()

            # 이미지 생성
            response = model.generate_images(
                prompt=prompt,
                number_of_images=num_images,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
                safety_filter_level="block_few",
                person_generation="allow_adult",
            )

            # 이미지 저장
            output_paths = []
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            for i, image in enumerate(response.images):
                if num_images == 1:
                    save_path = output_path
                else:
                    base = Path(output_path)
                    save_path = str(base.parent / f"{base.stem}_{i}{base.suffix}")

                image.save(location=save_path)
                output_paths.append(save_path)
                print(f"[Gemini] Image saved: {save_path}")

            return output_paths

        except Exception as e:
            print(f"[Gemini] Image generation error: {e}")
            raise

    async def analyze_image(
        self,
        image_path: str,
        prompt: str,
    ) -> str:
        """이미지 분석"""
        image = Image.open(image_path)

        response = self.client.models.generate_content(
            model=self.model,
            contents=[image, prompt]
        )

        return response.text

    async def analyze_video(
        self,
        video_path: str,
        prompt: str,
        num_frames: int = 5,
    ) -> str:
        """비디오 분석 (프레임 추출 방식)"""
        frames = self._extract_video_frames(video_path, num_frames)

        contents = []
        for i, frame in enumerate(frames):
            contents.append(f"Frame {i+1}/{len(frames)}:")
            contents.append(frame)
        contents.append(prompt)

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents
        )

        return response.text

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """JSON 응답 파싱"""
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                parts = response.split("```")
                if len(parts) >= 2:
                    response = parts[1]
            return json.loads(response.strip())
        except:
            return {"raw_response": response, "parse_error": True}

    async def generate_prompt(
        self,
        script_line: str,
        character_style: str = "Worzak-style financial cartoon",
    ) -> Dict[str, Any]:
        """대본에서 이미지/영상 프롬프트 생성"""
        system_prompt = f"""You are a visual storyboard engineer for YouTube finance videos.

Given this script line: "{script_line}"

Generate image and video prompts following these rules:

IMAGE PROMPT REQUIREMENTS:
- Full body shot of character (head to toe visible)
- Style: {character_style}
- Young Korean character
- White or light solid background
- Bold black outlines, flat clean colors
- Exaggerated facial expression matching the script
- Minimal props if needed (money, receipts, calendar, clock, arrows, charts)
- No text in image
- Clean composition suitable for thumbnail

VIDEO PROMPT REQUIREMENTS:
- Subtle natural movements of the full-body character
- Allowed: eye blinks, breathing, slight head tilt, small hand/arm movement
- Prop animation: money floating, calendar flipping, clock hands moving
- Effects: slow zoom in or gentle parallax
- No camera shake, fast cuts, or character cropping
- Duration: 3-5 seconds
- Mood: calm and clean

Respond in JSON format:
{{"image_prompt": "English image prompt", "video_prompt": "English video prompt", "expression": "Expression in Korean", "props": ["list of props"]}}

JSON only:"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=[system_prompt]
        )

        return self._parse_json_response(response.text)

    async def quality_check_image(self, image_path: str) -> Dict[str, Any]:
        """이미지 퀄리티 체크"""
        prompt = """이 이미지의 품질을 분석해주세요. 다음 JSON 형식으로 응답해주세요:
{
    "overall_score": 1-10 점수,
    "composition_score": 1-10 (구도),
    "color_quality": 1-10 (색상 품질),
    "character_visibility": 1-10 (캐릭터 가시성),
    "background_cleanliness": 1-10 (배경 깔끔함),
    "style_consistency": 1-10 (스타일 일관성),
    "issues": ["발견된 문제점 목록"],
    "suggestions": ["개선 제안 목록"],
    "summary": "품질 요약 (한국어)"
}

평가 기준:
- 캐릭터 전신이 머리부터 발끝까지 보이는가?
- 배경이 깨끗한가 (흰색/밝은색 선호)?
- 색상이 깔끔하고 평면적인가 (카툰 스타일)?
- 외곽선이 굵고 선명한가?
- 흐림, 왜곡, 아티팩트가 있는가?

JSON만 응답해주세요."""

        response = await self.analyze_image(image_path, prompt)
        return self._parse_json_response(response)

    async def quality_check_video(self, video_path: str) -> Dict[str, Any]:
        """비디오 퀄리티 체크"""
        prompt = """이 비디오 프레임들의 품질을 분석해주세요. 다음 JSON 형식으로 응답해주세요:
{
    "overall_score": 1-10 점수,
    "motion_quality": 1-10 (모션 품질),
    "frame_consistency": 1-10 (프레임 일관성),
    "character_preservation": 1-10 (캐릭터 보존),
    "color_stability": 1-10 (색상 안정성),
    "artifacts": 1-10 (10=아티팩트 없음),
    "issues": ["발견된 문제점 목록"],
    "suggestions": ["개선 제안 목록"],
    "summary": "품질 요약 (한국어)"
}

평가 기준:
- 캐릭터가 프레임 전체에서 인식 가능하고 일관적인가?
- 부드러운 모션인가 급격한 변화가 있는가?
- 흰색/빈 프레임이나 색이 바랜 부분이 있는가?
- 시각적 아티팩트, 흐림, 왜곡이 있는가?
- 애니메이션이 자연스러운가 (미세한 호흡, 눈 깜빡임)?

JSON만 응답해주세요."""

        response = await self.analyze_video(video_path, prompt, num_frames=5)
        return self._parse_json_response(response)

    async def compare_quality(
        self,
        image_paths: List[str] = None,
        video_paths: List[str] = None
    ) -> Dict[str, Any]:
        """여러 이미지/비디오 품질 비교"""
        contents = []

        if image_paths:
            contents.append("다음 이미지들을 비교 분석해주세요:")
            for i, path in enumerate(image_paths):
                contents.append(f"이미지 {i+1}:")
                contents.append(Image.open(path))

        if video_paths:
            contents.append("다음 비디오들의 프레임을 비교 분석해주세요:")
            for i, path in enumerate(video_paths):
                frames = self._extract_video_frames(path, num_frames=3)
                contents.append(f"비디오 {i+1}:")
                for frame in frames:
                    contents.append(frame)

        contents.append("""
각 항목의 품질을 비교하고 순위를 매겨주세요. JSON 형식으로 응답:
{
    "ranking": [{"rank": 1, "item": "이미지/비디오 번호", "score": 점수, "reason": "이유"}],
    "best_choice": "가장 좋은 항목 번호",
    "comparison_summary": "비교 요약 (한국어)"
}

JSON만 응답해주세요.
""")

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents
        )

        return self._parse_json_response(response.text)


# 싱글톤 인스턴스
gemini_service = GeminiService()
