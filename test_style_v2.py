#!/usr/bin/env python3
"""Family Guy 스타일 + 파란 양복 강화 테스트"""

import asyncio
import sys
import base64

sys.path.append("/data/routine/routine-studio-v2")

from apps.api.services.comfyui import comfyui_service
from apps.api.services.workflow import workflow_service

REF_IMAGE_PATH = "/data/routine/routine-studio-v2/test_images/family_guy_ref.b64"
OUTPUT_DIR = "/data/routine/routine-studio-v2/output"

async def test_v2():
    with open(REF_IMAGE_PATH, "r") as f:
        ref_b64 = f.read().strip()
    
    print(f"레퍼런스 이미지: {len(ref_b64)} bytes")
    
    # 파란 양복 강조 + 스타일 weight 조정
    tests = [
        {
            "name": "v2_w90_blue_emphasis",
            "prompt": "solo, 1man, asian man, korean businessman, BLACK HAIR, wearing NAVY BLUE SUIT, DARK BLUE formal suit jacket, blue tie, cartoon style, family guy style, simple white background, standing",
            "negative": "white clothes, white shirt, white suit, realistic, photorealistic, 3d, lowres, bad anatomy, text, blurry, multiple people",
            "weight": 0.90,
            "weight_type": "strong style transfer",
            "cfg": 7.5,
            "steps": 35,
            "checkpoint": "animagineXL_v31.safetensors"
        },
        {
            "name": "v2_nova_cartoon",
            "prompt": "solo, 1man, east asian male, black hair, wearing dark blue suit, navy blue business suit, blue necktie, cartoon character, american cartoon style, simple background",
            "negative": "white clothes, white shirt, realistic, photo, 3d render, lowres, bad anatomy, multiple people",
            "weight": 0.85,
            "weight_type": "style transfer",
            "cfg": 6.0,
            "steps": 30,
            "checkpoint": "NovaCartoonXL_v6.safetensors"
        },
        {
            "name": "v2_linear_w95",
            "prompt": "solo, 1person, asian man businessman, black hair, BLUE SUIT, navy blue jacket, blue formal wear, cartoon, family guy art style, white background",
            "negative": "white clothes, white outfit, realistic, 3d, lowres, blurry, multiple people, crowd",
            "weight": 0.95,
            "weight_type": "linear",
            "cfg": 7.0,
            "steps": 35,
            "checkpoint": "animagineXL_v31.safetensors"
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"\n{'='*50}")
        print(f"테스트: {test['name']}")
        print(f"Checkpoint: {test['checkpoint']}")
        print(f"Weight: {test['weight']}, Type: {test['weight_type']}")
        print(f"{'='*50}")
        
        try:
            workflow = workflow_service.build_ipadapter_style_transfer(
                positive_prompt=test["prompt"],
                reference_image_b64=ref_b64,
                negative_prompt=test["negative"],
                checkpoint=test["checkpoint"],
                ipadapter_weight=test["weight"],
                weight_type=test["weight_type"],
                style="cartoon",
                cfg=test["cfg"],
                steps=test["steps"],
                width=1024,
                height=1024
            )
            
            print("이미지 생성 중...")
            images = await comfyui_service.execute_workflow(workflow, timeout=300)
            
            if images:
                img_data = images[0]
                if img_data.startswith("data:"):
                    img_data = img_data.split(",", 1)[1]
                
                output_path = f"{OUTPUT_DIR}/{test['name']}.png"
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(img_data))
                
                print(f"✅ 저장: {output_path}")
                results.append(output_path)
            else:
                print("❌ 실패")
                
        except Exception as e:
            print(f"❌ 오류: {e}")
    
    print(f"\n완료: {len(results)}/{len(tests)}")
    return results

if __name__ == "__main__":
    asyncio.run(test_v2())
