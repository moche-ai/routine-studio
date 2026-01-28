#!/usr/bin/env python3
"""Family Guy 스타일 유지 + 동양인 파란 양복 캐릭터 생성 테스트"""

import asyncio
import sys
import base64
from pathlib import Path

sys.path.append("/data/routine/routine-studio-v2")

from apps.api.services.comfyui import comfyui_service
from apps.api.services.workflow import workflow_service

REF_IMAGE_PATH = "/data/routine/routine-studio-v2/test_images/family_guy_ref.b64"
OUTPUT_DIR = "/data/routine/routine-studio-v2/output"

async def test_style_transfer():
    # 레퍼런스 이미지 로드
    with open(REF_IMAGE_PATH, "r") as f:
        ref_b64 = f.read().strip()
    
    print(f"레퍼런스 이미지 로드: {len(ref_b64)} bytes")
    
    # 테스트 설정들
    tests = [
        {
            "name": "w75_style_transfer",
            "prompt": "solo, 1person, asian man, east asian male, black hair, wearing blue suit, blue formal suit, standing, simple background, white background",
            "weight": 0.75,
            "weight_type": "style transfer precise",
            "cfg": 6.5,
            "steps": 30
        },
        {
            "name": "w80_style_transfer",
            "prompt": "solo, 1person, asian man, east asian male, black hair, wearing blue suit, blue business suit, standing pose, simple background",
            "weight": 0.80,
            "weight_type": "style transfer",
            "cfg": 7.0,
            "steps": 30
        },
        {
            "name": "w85_strong_style",
            "prompt": "solo, 1person, asian man, korean man, black hair, blue suit, formal attire, cartoon style, simple background",
            "weight": 0.85,
            "weight_type": "strong style transfer",
            "cfg": 7.0,
            "steps": 35
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"\n{'='*50}")
        print(f"테스트: {test['name']}")
        print(f"Weight: {test['weight']}, Type: {test['weight_type']}")
        print(f"='*50")
        
        try:
            workflow = workflow_service.build_ipadapter_style_transfer(
                positive_prompt=test["prompt"],
                reference_image_b64=ref_b64,
                negative_prompt="lowres, bad anatomy, text, error, worst quality, low quality, blurry, deformed, multiple people, 2girls, 2boys, realistic, photorealistic, 3d render",
                checkpoint="animagineXL_v31.safetensors",
                ipadapter_weight=test["weight"],
                weight_type=test["weight_type"],
                style="cartoon",
                cfg=test["cfg"],
                steps=test["steps"],
                width=1024,
                height=1024
            )
            
            print("워크플로우 생성 완료, 이미지 생성 중...")
            images = await comfyui_service.execute_workflow(workflow, timeout=300)
            
            if images:
                img_data = images[0]
                if img_data.startswith("data:"):
                    img_data = img_data.split(",", 1)[1]
                
                output_path = f"{OUTPUT_DIR}/fg_asian_blue_{test['name']}.png"
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(img_data))
                
                print(f"✅ 저장: {output_path}")
                results.append(output_path)
            else:
                print("❌ 이미지 생성 실패")
                
        except Exception as e:
            print(f"❌ 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*50}")
    print(f"완료: {len(results)}/{len(tests)} 성공")
    print(f"결과 이미지: {OUTPUT_DIR}/fg_asian_blue_*.png")
    return results

if __name__ == "__main__":
    asyncio.run(test_style_transfer())
