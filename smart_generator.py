#!/usr/bin/env python3
"""Smart Character Generator with Quality Validation Loop"""

import asyncio
import sys
import os
import random
import base64
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

sys.path.append("/data/routine/routine-studio-v2")
sys.path.append("/data/routine/routine-studio-v2/apps/api")

from services.comfyui import comfyui_service
from services.vision import vision_service


class SmartCharacterGenerator:
    """품질 검증이 포함된 캐릭터 생성기"""

    VALIDATION_PROMPT = """Analyze this cartoon character and answer in JSON:
1. character_count: How many people? (number)
2. face_quality: Clear, well-drawn face features? (1-10)
3. suit_color: Main clothing color? ("blue", "white", etc.)
4. has_deformities: Any anatomical issues? (true/false)
5. quality_score: Overall quality (1-10)

Return ONLY JSON: {"character_count": 1, "face_quality": 7, "suit_color": "blue", "has_deformities": false, "quality_score": 7}"""

    def __init__(self, max_attempts: int = 5, min_quality: int = 7):
        self.max_attempts = max_attempts
        self.min_quality = min_quality

    async def validate_image(self, image_b64: str, expected_color: str = "blue") -> Tuple[bool, Dict, str]:
        """이미지 검증"""
        try:
            result = await vision_service.analyze_image(image_b64, self.VALIDATION_PROMPT)

            if "{" in result:
                import json
                analysis = json.loads(result[result.find("{"):result.rfind("}")+1])
            else:
                return False, {}, "Parse error"

            failures = []

            if analysis.get("character_count", 0) != 1:
                failures.append(f"chars={analysis.get('character_count')}")

            if analysis.get("face_quality", 0) < 7:
                failures.append(f"face={analysis.get('face_quality')}/10")

            suit_color = analysis.get("suit_color", "").lower()
            if expected_color.lower() not in suit_color:
                failures.append(f"color={suit_color}")

            if analysis.get("has_deformities", True):
                failures.append("deformed")

            if analysis.get("quality_score", 0) < self.min_quality:
                failures.append(f"quality={analysis.get('quality_score')}/10")

            passed = len(failures) == 0
            return passed, analysis, ", ".join(failures) if failures else "OK"

        except Exception as e:
            return False, {}, str(e)

    async def generate_with_validation(
        self,
        reference_image_b64: str,
        positive_prompt: str,
        negative_prompt: str,
        expected_color: str = "blue",
        ipadapter_weight: float = 0.5  # Lower weight for better prompt adherence
    ) -> Tuple[Optional[str], Dict, int]:
        """검증 통과할 때까지 생성 반복"""

        for attempt in range(1, self.max_attempts + 1):
            print(f"\n  Attempt {attempt}/{self.max_attempts}...")

            # 워크플로우 생성
            seed = random.randint(0, 2**32 - 1)
            workflow = self._build_workflow(
                reference_image_b64, positive_prompt, negative_prompt,
                ipadapter_weight, seed
            )

            try:
                images = await comfyui_service.execute_workflow(workflow, timeout=180)
                if not images:
                    print(f"    No image generated")
                    continue

                image_b64 = images[0]
                if image_b64.startswith("data:"):
                    image_b64 = image_b64.split(",", 1)[1]

                # 검증
                passed, analysis, reason = await self.validate_image(image_b64, expected_color)

                quality = analysis.get("quality_score", 0)
                print(f"    Quality: {quality}/10 | {'PASS' if passed else 'FAIL'}: {reason}")

                if passed:
                    return image_b64, analysis, attempt

            except Exception as e:
                print(f"    Error: {e}")

        return None, {}, self.max_attempts

    def _build_workflow(self, ref_b64, pos, neg, weight, seed) -> Dict:
        return {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "animagineXL_v31.safetensors"}},
            "2": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}},
            "3": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}},
            "4": {"class_type": "ETN_LoadImageBase64", "inputs": {"image": ref_b64}},
            "5": {"class_type": "IPAdapterAdvanced", "inputs": {
                "model": ["1", 0], "ipadapter": ["3", 0], "clip_vision": ["2", 0], "image": ["4", 0],
                "weight": weight, "weight_type": "style transfer precise",
                "combine_embeds": "concat", "start_at": 0.0, "end_at": 0.8, "embeds_scaling": "V only"
            }},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["1", 1]}},
            "8": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
            "9": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": 35, "cfg": 8.5, "sampler_name": "euler", "scheduler": "normal",
                "denoise": 1.0, "model": ["5", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["8", 0]
            }},
            "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["1", 2]}},
            "11": {"class_type": "SaveImage", "inputs": {"filename_prefix": "smart_gen", "images": ["10", 0]}}
        }


async def main():
    generator = SmartCharacterGenerator(max_attempts=5, min_quality=7)

    # Load reference (blue suit character)
    with open("/data/routine/routine-studio-v2/test_images/ref_image2.b64", "r") as f:
        ref_image = f.read().strip()

    # Strong prompt for blue suit
    positive = "solo, 1person, single character, (dark blue suit:1.4), (navy blue business suit:1.3), blue jacket, blue pants, necktie, asian man, cartoon style, family guy style, clean lines, simple background"
    negative = "multiple people, 2girls, 2boys, white suit, white clothes, gray suit, realistic, photograph, bad hands, extra fingers, deformed"

    print("=" * 60)
    print("Smart Character Generator with Quality Validation")
    print("=" * 60)

    output_dir = "/data/routine/routine-studio-v2/output"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Generate 3 validated images
    for i in range(3):
        print(f"\n[Image {i+1}/3]")
        image_b64, analysis, attempts = await generator.generate_with_validation(
            ref_image, positive, negative, "blue", ipadapter_weight=0.45
        )

        if image_b64:
            filename = f"{output_dir}/smart_{i+1}_{timestamp}.png"
            with open(filename, "wb") as f:
                f.write(base64.b64decode(image_b64))
            print(f"  SAVED: {filename} (attempts: {attempts})")
        else:
            print(f"  FAILED after {attempts} attempts")


if __name__ == "__main__":
    asyncio.run(main())
