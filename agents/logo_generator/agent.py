"""YouTube 채널 브랜딩 에이전트 (로고, 배너, 워터마크)"""
from agents.config import agent_settings

import sys
import os
import json
import base64
import asyncio
import aiohttp
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum
from datetime import datetime

sys.path.append("/app")

from agents.base import BaseAgent, AgentResult, AgentStatus


class BrandingPhase(Enum):
    ASK_TYPE = "ask_type"       # 로고/배너/워터마크 선택
    GENERATING = "generating"
    REVIEW = "review"
    COMPLETE = "complete"


class BrandingType(Enum):
    LOGO = "logo"           # 800x800 (프로필)
    BANNER = "banner"       # 2560x1440 (채널 아트)
    WATERMARK = "watermark" # 150x150 (투명 워터마크)


# 카테고리별 스타일 가이드라인 (Gemini 추천)
CATEGORY_GUIDELINES = {
    "경제": {
        "style": "Professional, Modern, Clean",
        "color_palette": "blue, green, gray, gold",
        "imagery": "charts, graphs, money symbols, buildings, growth arrows",
        "banner_elements": "cityscape, financial district, stock charts background"
    },
    "게임": {
        "style": "Energetic, Vibrant, Playful",
        "color_palette": "red, orange, purple, neon colors",
        "imagery": "controllers, game characters, pixel art, explosions, power-ups",
        "banner_elements": "gaming setup, neon lights, action scenes"
    },
    "교육": {
        "style": "Informative, Friendly, Approachable",
        "color_palette": "blue, green, yellow, white",
        "imagery": "books, pencils, lightbulbs, graduation caps",
        "banner_elements": "classroom, study desk, knowledge symbols"
    },
    "엔터테인먼트": {
        "style": "Creative, Fun, Engaging",
        "color_palette": "bright and varied, pink, yellow, cyan",
        "imagery": "microphones, cameras, stars, spotlights",
        "banner_elements": "stage lights, entertainment venue, vibrant patterns"
    },
    "기술": {
        "style": "Modern, Sleek, Innovative",
        "color_palette": "blue, silver, black, cyan",
        "imagery": "circuits, code, robots, futuristic elements",
        "banner_elements": "tech workspace, digital patterns, futuristic cityscape"
    },
    "라이프스타일": {
        "style": "Warm, Inviting, Personal",
        "color_palette": "earth tones, pastels, warm colors",
        "imagery": "nature, coffee, cozy elements, daily life",
        "banner_elements": "cozy room, lifestyle scene, natural elements"
    },
    "default": {
        "style": "Modern, Clean, Memorable",
        "color_palette": "vibrant colors",
        "imagery": "abstract shapes, bold typography",
        "banner_elements": "abstract geometric patterns, gradient backgrounds"
    }
}

# 브랜딩 타입별 설정
BRANDING_SPECS = {
    BrandingType.LOGO: {
        "width": 1024,
        "height": 1024,
        "description": "프로필 이미지용 로고",
        "prompt_suffix": "circular logo design, centered composition, clean background, suitable for profile picture, high quality",
        "negative": "text, words, letters, watermark, blurry, cropped"
    },
    BrandingType.BANNER: {
        "width": 2560,
        "height": 1440,
        "description": "채널 배너 아트",
        "prompt_suffix": "YouTube channel banner art, wide panoramic composition, space for text on sides, professional channel art, cinematic lighting",
        "negative": "text, words, watermark, blurry, low quality, cropped edges"
    },
    BrandingType.WATERMARK: {
        "width": 512,
        "height": 512,
        "description": "영상 워터마크 (구독 버튼용)",
        "prompt_suffix": "simple icon design, minimal, clean lines, works on transparent background, subscribe button style, single color friendly",
        "negative": "complex details, photorealistic, background, text, multiple colors"
    }
}


class LogoGeneratorAgent(BaseAgent):
    """YouTube 채널 브랜딩 생성 에이전트 (로고, 배너, 워터마크)"""
    
    COMFYUI_URL = agent_settings.comfyui_url
    OUTPUT_DIR = Path("/app/output/branding")
    
    def __init__(self):
        super().__init__("LogoGeneratorAgent")
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.phase = BrandingPhase.ASK_TYPE
        self.branding_type = BrandingType.LOGO
        self.generated_images = []
        self.context = {}
        
    def _get_category_guidelines(self, category: str) -> dict:
        """카테고리에 맞는 스타일 가이드 반환"""
        category_lower = category.lower() if category else ""
        
        for key, guidelines in CATEGORY_GUIDELINES.items():
            if key != "default" and key in category_lower:
                return guidelines
        
        # 키워드 매칭
        if any(k in category_lower for k in ["경제", "금융", "투자", "주식", "비즈니스"]):
            return CATEGORY_GUIDELINES["경제"]
        elif any(k in category_lower for k in ["게임", "gaming", "esports"]):
            return CATEGORY_GUIDELINES["게임"]
        elif any(k in category_lower for k in ["교육", "강의", "학습", "tutorial"]):
            return CATEGORY_GUIDELINES["교육"]
        elif any(k in category_lower for k in ["기술", "tech", "it", "프로그래밍", "코딩"]):
            return CATEGORY_GUIDELINES["기술"]
        elif any(k in category_lower for k in ["라이프", "일상", "vlog", "브이로그"]):
            return CATEGORY_GUIDELINES["라이프스타일"]
        
        return CATEGORY_GUIDELINES["default"]
    
    def _build_prompt(
        self,
        branding_type: BrandingType,
        channel_name: str,
        character_info: dict,
        style: str,
        category: str
    ) -> dict:
        """브랜딩 타입별 프롬프트 생성"""
        guidelines = self._get_category_guidelines(category)
        specs = BRANDING_SPECS[branding_type]
        
        # 캐릭터 정보 추출
        char_type = character_info.get("character_type", "character")
        gender = character_info.get("gender", "")
        art_style = character_info.get("art_style", style)
        personality = character_info.get("personality", "")
        expression = character_info.get("expression", "friendly")
        
        prompt_parts = []
        
        if branding_type == BrandingType.LOGO:
            prompt_parts = [
                f"YouTube channel logo for '{channel_name}'",
                f"{guidelines['style']} style",
                f"featuring a {char_type}",
                f"{art_style} art style",
                f"color palette: {guidelines['color_palette']}",
            ]
            if gender:
                prompt_parts.append(f"{gender}")
            if personality:
                prompt_parts.append(f"{personality} vibe")
                
        elif branding_type == BrandingType.BANNER:
            prompt_parts = [
                f"YouTube channel banner for '{channel_name}'",
                f"{guidelines['style']} style",
                guidelines.get('banner_elements', 'abstract background'),
                f"featuring {char_type} character on the right side",
                f"{art_style} art style",
                f"color palette: {guidelines['color_palette']}",
                "wide panoramic view",
                "professional quality"
            ]
            
        elif branding_type == BrandingType.WATERMARK:
            prompt_parts = [
                "simple minimal icon",
                f"{char_type} silhouette",
                f"{guidelines['color_palette'].split(',')[0]} color",
                "clean vector style",
                "suitable for watermark"
            ]
        
        prompt_parts.append(specs["prompt_suffix"])
        
        return {
            "positive": ", ".join(prompt_parts),
            "negative": specs["negative"]
        }
    
    async def _generate_with_comfyui(
        self, 
        prompt: dict, 
        session_id: str,
        width: int,
        height: int,
        batch_size: int = 2
    ) -> List[str]:
        """ComfyUI로 이미지 생성"""
        import uuid
        
        # SDXL 워크플로우 (해상도에 따라 조정)
        # 배너는 너무 크면 OOM 발생할 수 있으므로 1280x720으로 생성 후 업스케일 권장
        actual_width = min(width, 1536)
        actual_height = min(height, 1024)
        
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": int(datetime.now().timestamp()) % (2**32),
                    "steps": 25,
                    "cfg": 7.5,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "juggernautXL_v9.safetensors"
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": actual_width,
                    "height": actual_height,
                    "batch_size": batch_size
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt["positive"],
                    "clip": ["4", 1]
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt["negative"],
                    "clip": ["4", 1]
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": f"branding_{self.branding_type.value}_{session_id}",
                    "images": ["8", 0]
                }
            }
        }
        
        client_id = str(uuid.uuid4())
        
        async with aiohttp.ClientSession() as session:
            # 워크플로우 실행
            async with session.post(
                f"{self.COMFYUI_URL}/prompt",
                json={"prompt": workflow, "client_id": client_id}
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"ComfyUI error: {await resp.text()}")
                data = await resp.json()
                prompt_id = data.get("prompt_id")
            
            # 결과 대기
            max_wait = 180  # 배너는 시간이 더 걸릴 수 있음
            for _ in range(max_wait):
                await asyncio.sleep(1)
                async with session.get(f"{self.COMFYUI_URL}/history/{prompt_id}") as resp:
                    history = await resp.json()
                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})
                        if "9" in outputs and outputs["9"].get("images"):
                            images = []
                            for img_info in outputs["9"]["images"]:
                                filename = img_info["filename"]
                                subfolder = img_info.get("subfolder", "")
                                
                                # 이미지 다운로드
                                params = {"filename": filename, "subfolder": subfolder, "type": "output"}
                                async with session.get(f"{self.COMFYUI_URL}/view", params=params) as img_resp:
                                    img_data = await img_resp.read()
                                    
                                    # 저장
                                    save_path = self.OUTPUT_DIR / f"{session_id}_{self.branding_type.value}_{filename}"
                                    with open(save_path, "wb") as f:
                                        f.write(img_data)
                                    
                                    # Base64 인코딩
                                    images.append(base64.b64encode(img_data).decode())
                            
                            return images
            
            raise Exception("Branding generation timeout")
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """브랜딩 생성 시작"""
        self.status = AgentStatus.RUNNING
        self.context = input_data
        
        # 브랜딩 타입 확인
        branding_type_str = input_data.get("branding_type", "logo")
        try:
            self.branding_type = BrandingType(branding_type_str)
        except:
            self.branding_type = BrandingType.LOGO
        
        # context에서 정보 추출
        channel_name = input_data.get("channel_name", "")
        character_info = input_data.get("character_info", {})
        style = input_data.get("style", "cartoon")
        category = input_data.get("category", "")
        session_id = input_data.get("session_id", "unknown")
        
        if not channel_name:
            return AgentResult(
                success=False,
                step="branding",
                message="채널명이 필요합니다.",
                needs_feedback=False
            )
        
        specs = BRANDING_SPECS[self.branding_type]
        prompt = self._build_prompt(self.branding_type, channel_name, character_info, style, category)
        guidelines = self._get_category_guidelines(category)
        
        type_names = {
            BrandingType.LOGO: "로고",
            BrandingType.BANNER: "배너",
            BrandingType.WATERMARK: "워터마크"
        }
        type_name = type_names.get(self.branding_type, "이미지")
        
        message = f"""🎨 **{channel_name}** 채널 {type_name}를 생성합니다!

**타입:** {specs['description']} ({specs['width']}x{specs['height']})
**스타일:** {guidelines['style']}
**색상:** {guidelines['color_palette']}

생성 중... (약 30-60초 소요)"""
        
        self.phase = BrandingPhase.GENERATING
        
        try:
            # ComfyUI로 이미지 생성
            images = await self._generate_with_comfyui(
                prompt, 
                session_id,
                specs['width'],
                specs['height']
            )
            self.generated_images = images
            
            self.phase = BrandingPhase.REVIEW
            self.status = AgentStatus.WAITING_FEEDBACK
            
            return AgentResult(
                success=True,
                step="logo_review",
                message=f"""✅ **{type_name} {len(images)}개가 생성되었습니다!**

마음에 드는 {type_name}를 선택해주세요.
- 숫자를 입력하면 해당 이미지가 선택됩니다.
- "다시"를 입력하면 새로운 {type_name}를 생성합니다.""",
                needs_feedback=True,
                data={
                    "type": "branding_selection",
                    "branding_type": self.branding_type.value,
                    "images": images,
                    "prompt_used": prompt["positive"]
                }
            )
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(
                success=False,
                step="branding",
                message=f"{type_name} 생성 중 오류가 발생했습니다: {str(e)}",
                needs_feedback=False
            )
    
    async def handle_feedback(self, feedback: str, context: Dict[str, Any] = None) -> AgentResult:
        """사용자 피드백 처리 (BaseAgent 추상 메서드 구현)"""
        return await self.process_feedback(feedback, context)
    
    async def process_feedback(self, feedback: str, context: Dict[str, Any] = None) -> AgentResult:
        """사용자 피드백 처리"""
        feedback_lower = feedback.lower().strip()
        
        type_names = {
            BrandingType.LOGO: "로고",
            BrandingType.BANNER: "배너", 
            BrandingType.WATERMARK: "워터마크"
        }
        type_name = type_names.get(self.branding_type, "이미지")
        
        if self.phase == BrandingPhase.REVIEW:
            # "다시" 선택
            if "다시" in feedback_lower or "regenerate" in feedback_lower or "재생성" in feedback_lower:
                return await self.execute(context or self.context)
            
            # 숫자 선택
            try:
                selection = int(feedback_lower) - 1
                if 0 <= selection < len(self.generated_images):
                    selected_image = self.generated_images[selection]
                    self.phase = BrandingPhase.COMPLETE
                    self.status = AgentStatus.COMPLETED
                    
                    return AgentResult(
                        success=True,
                        step="logo_complete",
                        message=f"✅ {type_name} {selection + 1}번이 선택되었습니다!",
                        needs_feedback=False,
                        data={
                            "selected_image": selected_image,
                            "branding_type": self.branding_type.value,
                            "selection_index": selection
                        }
                    )
            except ValueError:
                pass
            
            return AgentResult(
                success=True,
                step="logo_review",
                message=f"숫자를 입력하거나 '다시'를 입력해주세요. (1-{len(self.generated_images)})",
                needs_feedback=True
            )
        
        return AgentResult(
            success=False,
            step="branding",
            message="예상치 못한 상태입니다.",
            needs_feedback=False
        )
