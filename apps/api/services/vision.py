import httpx
import base64
import json
import re
from typing import Optional, Dict, Any, Callable, AsyncGenerator

class VisionService:
    """Qwen3-VL 비전 모델 서비스 (Instruct 모델)"""

    STYLE_TYPES = {
        "cartoon": "cartoon, animated, family guy, simpsons, south park, american cartoon, flat colors, bold outlines",
        "anime": "anime, manga, japanese animation, cel shaded, large eyes, japanese style",
        "realistic": "realistic, photorealistic, photograph, real person, detailed skin, natural lighting",
        "3d": "3d render, 3d model, cgi, pixar style, rendered, digital 3d",
        "illustration": "illustration, digital art, concept art, painted, artistic style",
        "pixel": "pixel art, 8bit, 16bit, retro game style"
    }

    def __init__(self, base_url: str = None):
        # Docker 컨테이너에서 호스트 접근: 172.17.0.1 또는 host.docker.internal
        import os
        self.base_url = base_url or os.environ.get("VISION_API_URL", "http://172.17.0.1:8016/v1")
        self.model = os.environ.get("VISION_MODEL", "qwen3-vl-30b")  # Match actual model name

    def _extract_json(self, content: str) -> Optional[dict]:
        """응답에서 JSON 추출"""
        # JSON 블록 찾기
        if "```json" in content:
            match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass

        # 일반 JSON 찾기
        matches = re.findall(r'\{[^{}]*\}', content, re.DOTALL)
        for match in reversed(matches):
            try:
                return json.loads(match)
            except:
                continue

        # 중첩 JSON 시도
        if "{" in content and "}" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            try:
                return json.loads(content[start:end])
            except:
                pass

        return None

    async def analyze_image_stream(
        self,
        image_data: str,
        prompt: str,
        max_tokens: int = 1024,
        on_thinking: Optional[Callable[[str], None]] = None,
        on_answer: Optional[Callable[[str], None]] = None
    ) -> Dict[str, str]:
        """이미지 분석 (스트리밍) - Instruct 모델용"""
        if image_data.startswith("data:"):
            image_url = image_data
        else:
            image_url = f"data:image/png;base64,{image_data}"

        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt}
            ]
        }]

        full_content = ""

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        chunk = delta.get("content", "")

                        if chunk:
                            full_content += chunk
                            if on_answer:
                                on_answer(full_content)
                    except json.JSONDecodeError:
                        continue

        return {
            "thinking": "",  # Instruct 모델은 thinking 없음
            "answer": full_content,
            "raw": full_content
        }

    async def analyze_image(
        self,
        image_data: str,
        prompt: str = "Describe this image in detail for image generation.",
        max_tokens: int = 1024
    ) -> str:
        """이미지 분석"""
        if image_data.startswith("data:"):
            image_url = image_data
        else:
            image_url = f"data:image/png;base64,{image_data}"

        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt}
            ]
        }]

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def analyze_image_with_thinking(
        self,
        image_data: str,
        prompt: str = "Describe this image in detail for image generation.",
        max_tokens: int = 1024
    ) -> Dict[str, str]:
        """이미지 분석 (호환성 유지)"""
        content = await self.analyze_image(image_data, prompt, max_tokens)
        return {
            "thinking": "",
            "answer": content,
            "raw": content
        }

    async def analyze_style(self, image_data: str) -> Dict[str, Any]:
        """이미지 스타일 분석 및 분류"""

        prompt = """Analyze this image and classify its visual style.

Respond with ONLY a JSON object:
{
    "style": "cartoon or anime or realistic or 3d or illustration or pixel",
    "confidence": 0.0 to 1.0,
    "style_details": "specific style notes",
    "key_features": ["list", "of", "features"],
    "recommended_checkpoint": "cartoon for cartoon/family guy, anime for anime/manga, realistic for photos"
}

Be precise: Family Guy/Simpsons = cartoon, Japanese anime = anime, Photos = realistic."""

        try:
            response = await self.analyze_image(image_data, prompt, max_tokens=512)
            result = self._extract_json(response)

            if result:
                valid_styles = ["cartoon", "anime", "realistic", "3d", "illustration", "pixel"]
                if result.get("style") not in valid_styles:
                    result["style"] = "cartoon"
                return result

        except Exception as e:
            print(f"Style analysis failed: {e}")

        return {
            "style": "cartoon",
            "confidence": 0.5,
            "style_details": "Unable to analyze, defaulting to cartoon",
            "key_features": [],
            "recommended_checkpoint": "cartoon"
        }

    async def analyze_for_modification(self, image_data: str, user_feedback: str) -> str:
        """이미지 + 피드백을 분석하여 수정 방향 제안"""
        prompt = f"""Analyze this reference image.
User request: {user_feedback}

Describe:
1. Elements to incorporate from this image
2. Key visual characteristics
3. How to combine user request with image reference

Be specific for image generation."""

        return await self.analyze_image(image_data, prompt)

    async def describe_character(self, image_data: str) -> Dict[str, Any]:
        """캐릭터 이미지 상세 분석"""
        prompt = """Analyze this character image.

Respond with ONLY JSON:
{
    "character_type": "human/animal/robot/fantasy",
    "gender": "male/female/ambiguous",
    "body_type": "slim/average/muscular/heavy/stylized",
    "clothing": "clothing description",
    "hair": "hair description",
    "expression": "expression description",
    "pose": "pose description",
    "background": "background description",
    "art_style": "art style description"
}"""

        try:
            response = await self.analyze_image(image_data, prompt, max_tokens=768)
            result = self._extract_json(response)
            if result:
                return result
        except Exception as e:
            print(f"Character analysis failed: {e}")

        return {}

    async def describe_character_with_thinking(self, image_data: str) -> Dict[str, Any]:
        """캐릭터 이미지 상세 분석 (호환성 유지)"""
        prompt = """Analyze this character image carefully.

Respond with ONLY JSON:
{
    "character_type": "human/animal/robot/fantasy",
    "gender": "male/female/ambiguous",
    "body_type": "slim/average/muscular/heavy/stylized",
    "clothing": "clothing description",
    "hair": "hair description",
    "expression": "expression description",
    "pose": "pose description",
    "background": "background description",
    "art_style": "art style description",
    "personality_vibe": "what personality or vibe this character gives off"
}"""

        try:
            response = await self.analyze_image(image_data, prompt, max_tokens=1024)
            result = self._extract_json(response)
            if result:
                result["_thinking"] = ""  # 호환성
                return result
        except Exception as e:
            print(f"Character analysis failed: {e}")

        return {}

    async def analyze_character_for_edit(self, image_data: str, user_request: str) -> Dict[str, Any]:
        """편집을 위한 캐릭터 분석"""

        prompt = f"""Analyze this image for editing purposes.
User wants to: {user_request}

Respond with ONLY a JSON object:
{{
    "image_type": "cartoon" or "realistic" or "anime" or "3d" or "object",
    "character_type": "human" or "animal" or "object" or "abstract",
    "has_gender": true or false,
    "current_gender": "male" or "female" or "neutral" or "none",
    "current_features": {{
        "hair_color": "description or none",
        "clothing": "description or none",
        "accessories": "description or none",
        "skin_tone": "description or none"
    }},
    "edit_instruction": "Clear English instruction that makes sense for this specific image type",
    "recommended_denoise": 0.5 to 0.95,
    "notes": "Any special considerations for this edit"
}}

Important guidelines:
- For cartoon characters: denoise 0.70-0.85
- For realistic photos: denoise 0.60-0.75
- For major changes (gender, species): denoise 0.85-0.95
- For minor changes (color, accessory): denoise 0.60-0.75"""

        try:
            response = await self.analyze_image(image_data, prompt, max_tokens=800)
            result = self._extract_json(response)
            if result:
                return result

        except Exception as e:
            print(f"Character edit analysis failed: {e}")

        return {
            "image_type": "cartoon",
            "character_type": "human",
            "has_gender": True,
            "current_gender": "neutral",
            "current_features": {},
            "edit_instruction": f"Edit the image: {user_request}",
            "recommended_denoise": 0.75,
            "notes": "Analysis failed, using defaults"
        }

    async def quality_check(
        self,
        reference_image: str,
        frame_images: list[str],
        strict: bool = True
    ) -> Dict[str, Any]:
        """AI 비디오 품질 검사 (캐릭터 일관성)"""

        content = []
        content.append({"type": "text", "text": "REFERENCE (original character):"})

        if reference_image.startswith("data:"):
            ref_url = reference_image
        else:
            ref_url = f"data:image/png;base64,{reference_image}"
        content.append({"type": "image_url", "image_url": {"url": ref_url}})

        for i, frame in enumerate(frame_images[:3]):
            content.append({"type": "text", "text": f"FRAME {i+1}:"})
            if frame.startswith("data:"):
                frame_url = frame
            else:
                frame_url = f"data:image/png;base64,{frame}"
            content.append({"type": "image_url", "image_url": {"url": frame_url}})

        if strict:
            content.append({"type": "text", "text": """
AI VIDEO QUALITY CHECK - Be STRICT!

This is AI-generated video. AI often FAILS to maintain character consistency.
Look for these COMMON AI FAILURES:

❌ FAIL conditions (score 1-4):
- Face MORPHS or DISTORTS between frames
- Character looks like DIFFERENT PERSON in any frame
- Hair style/color CHANGES
- Body proportions CHANGE
- Skin color/tone CHANGES significantly
- Eyes/nose/mouth shapes CHANGE

✅ PASS conditions (score 8-10):
- EXACT same character in ALL frames
- Face stays IDENTICAL (not just similar)
- No morphing or distortion

Be harsh. Most AI videos FAIL. Output JSON:
{"score": <1-10>, "verdict": "<PASS or FAIL>"}"""})
        else:
            content.append({"type": "text", "text": """
Check if video frames show the same character as reference.
Output JSON: {"score": <1-10>, "verdict": "<PASS or FAIL>"}"""})

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": content}],
                    "max_tokens": 200,
                    "temperature": 0.1
                }
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]

            result = self._extract_json(text)
            if result:
                return {
                    "success": True,
                    "score": result.get("score"),
                    "verdict": result.get("verdict"),
                    "raw": text
                }
            return {
                "success": False,
                "error": "JSON parse failed",
                "raw": text
            }

vision_service = VisionService()
