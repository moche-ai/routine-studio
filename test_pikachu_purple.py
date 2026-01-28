#!/usr/bin/env python3
import asyncio
import sys
import base64
import json
import random
from copy import deepcopy

sys.path.append("/data/routine/routine-studio-v2")
from apps.api.services.comfyui import comfyui_service

async def test():
    with open("/data/routine/routine-studio-v2/test_images/pikachu_captain.b64", "r") as f:
        ref_b64 = f.read().strip()
    
    print(f"이미지 로드: {len(ref_b64)} bytes")
    
    with open("/data/routine/routine-studio-v2/workflows/v2/qwen_edit_with_lora.json", "r") as f:
        template = json.load(f)
    
    # 보라색 피카츄 테스트
    tests = [
        {
            "name": "pikachu_purple",
            "instruction": "Change the yellow Pikachu to PURPLE color. Make all the yellow parts purple/violet. Keep the same pose, captain hat, and cartoon style.",
            "denoise": 0.75
        },
        {
            "name": "pikachu_purple_v2",
            "instruction": "Transform this Pikachu into a purple variant. Change yellow body to bright purple/violet color while keeping the hat, eyes, cheeks, and all other details the same.",
            "denoise": 0.75
        },
    ]
    
    for t in tests:
        print(f"\n테스트: {t['name']}")
        
        workflow = deepcopy(template["workflow"])
        workflow["1"]["inputs"]["image"] = ref_b64
        workflow["5"]["inputs"]["strength_model"] = 0.9
        workflow["6"]["inputs"]["prompt"] = t["instruction"]
        workflow["8"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        workflow["8"]["inputs"]["steps"] = 30
        workflow["8"]["inputs"]["cfg"] = 5.0
        workflow["8"]["inputs"]["denoise"] = t["denoise"]
        workflow["10"]["inputs"]["filename_prefix"] = t["name"]
        
        try:
            images = await comfyui_service.execute_workflow(workflow, timeout=300)
            if images:
                img = images[0].split(",", 1)[1] if images[0].startswith("data:") else images[0]
                path = f"/data/routine/routine-studio-v2/output/{t['name']}.png"
                with open(path, "wb") as f:
                    f.write(base64.b64decode(img))
                print(f"✅ {path}")
        except Exception as e:
            print(f"❌ {e}")

asyncio.run(test())
