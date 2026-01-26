import httpx
import base64
import json
from typing import Optional, Dict, Any

class VisionService:
    """Qwen3-VL 비전 모델 서비스"""
    
    STYLE_TYPES = {
        "cartoon": "cartoon, animated, family guy, simpsons, south park, american cartoon, flat colors, bold outlines",
        "anime": "anime, manga, japanese animation, cel shaded, large eyes, japanese style",
        "realistic": "realistic, photorealistic, photograph, real person, detailed skin, natural lighting",
        "3d": "3d render, 3d model, cgi, pixar style, rendered, digital 3d",
        "illustration": "illustration, digital art, concept art, painted, artistic style",
        "pixel": "pixel art, 8bit, 16bit, retro game style"
    }
    
    def __init__(self, base_url: str = "http://localhost:8015/v1"):
        self.base_url = base_url
        self.model = "qwen3-vl-8b"
    
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
        
        async with httpx.AsyncClient(timeout=60.0) as client:
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
            
            if "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                result = json.loads(response[start:end])
                
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
            if "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                return json.loads(response[start:end])
        except Exception as e:
            print(f"Character analysis failed: {e}")
        
        return {}

vision_service = VisionService()
