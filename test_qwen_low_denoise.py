#!/usr/bin/env python3
"""Qwen Edit - 극도로 낮은 denoise 테스트"""

import asyncio
import sys
import base64

sys.path.append("/data/routine/routine-studio-v2")

from apps.api.services.comfyui import comfyui_service
from apps.api.services.workflow import workflow_service

REF_IMAGE_PATH = "/data/routine/routine-studio-v2/test_images/family_guy_ref.b64"
OUTPUT_DIR = "/data/routine/routine-studio-v2/output"

async def test_low_denoise():
    with open(REF_IMAGE_PATH, "r") as f:
        ref_b64 = f.read().strip()
    
    print(f"레퍼런스 이미지: {len(ref_b64)} bytes")
    
    # 극도로 낮은 denoise 테스트
    tests = [
        {"name": "qwen_d05", "denoise": 0.05},
        {"name": "qwen_d08", "denoise": 0.08},
        {"name": "qwen_d10", "denoise": 0.10},
        {"name": "qwen_d12", "denoise": 0.12},
    ]
    
    edit_instruction = "Change the character to an Asian man with black hair wearing a dark navy blue formal suit. Keep the same cartoon style and clean lines."
    
    results = []
    
    for test in tests:
        print(f"\n{'='*50}")
        print(f"테스트: {test['name']} (denoise: {test['denoise']})")
        print(f"{'='*50}")
        
        try:
            workflow = workflow_service.build_qwen_image_edit(
                input_image_b64=ref_b64,
                edit_instruction=edit_instruction,
                denoise=test["denoise"],
                output_prefix=test["name"]
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
    asyncio.run(test_low_denoise())
