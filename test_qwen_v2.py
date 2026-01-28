#!/usr/bin/env python3
import asyncio
import sys
import base64

sys.path.append("/data/routine/routine-studio-v2")

from apps.api.services.comfyui import comfyui_service
from apps.api.services.workflow import workflow_service

async def test():
    with open("/data/routine/routine-studio-v2/test_images/family_guy_ref2.b64", "r") as f:
        ref_b64 = f.read().strip()
    
    print(f"이미지 로드: {len(ref_b64)} bytes")
    
    tests = [
        {"name": "d05", "denoise": 0.05},
        {"name": "d08", "denoise": 0.08},
        {"name": "d10", "denoise": 0.10},
    ]
    
    instruction = "Change to an Asian man with black hair wearing a navy blue suit. Keep exact same cartoon style and clean lines."
    
    for t in tests:
        print(f"\n테스트: denoise={t['denoise']}")
        try:
            workflow = workflow_service.build_qwen_image_edit(
                input_image_b64=ref_b64,
                edit_instruction=instruction,
                denoise=t["denoise"],
                output_prefix=f"fg_asian_{t['name']}"
            )
            
            images = await comfyui_service.execute_workflow(workflow, timeout=300)
            
            if images:
                img = images[0].split(",", 1)[1] if images[0].startswith("data:") else images[0]
                path = f"/data/routine/routine-studio-v2/output/fg_asian_{t['name']}.png"
                with open(path, "wb") as f:
                    f.write(base64.b64decode(img))
                print(f"✅ {path}")
        except Exception as e:
            print(f"❌ {e}")

asyncio.run(test())
