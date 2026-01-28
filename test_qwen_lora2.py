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
    with open("/data/routine/routine-studio-v2/test_images/family_guy_ref2.b64", "r") as f:
        ref_b64 = f.read().strip()
    
    with open("/data/routine/routine-studio-v2/workflows/v2/qwen_edit_with_lora.json", "r") as f:
        template = json.load(f)
    
    tests = [
        {"name": "lora_d75", "denoise": 0.75},
        {"name": "lora_d80", "denoise": 0.80},
        {"name": "lora_d85", "denoise": 0.85},
    ]
    
    instruction = "Transform into an Asian man with BLACK HAIR, wearing GLASSES and a bright RED SUIT jacket. Keep the cartoon style."
    
    for t in tests:
        print(f"테스트: {t['name']} (denoise={t['denoise']})")
        
        workflow = deepcopy(template["workflow"])
        workflow["1"]["inputs"]["image"] = ref_b64
        workflow["5"]["inputs"]["strength_model"] = 0.9
        workflow["6"]["inputs"]["prompt"] = instruction
        workflow["8"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        workflow["8"]["inputs"]["steps"] = 30
        workflow["8"]["inputs"]["cfg"] = 5.0
        workflow["8"]["inputs"]["denoise"] = t["denoise"]
        workflow["10"]["inputs"]["filename_prefix"] = f"fg_{t['name']}"
        
        try:
            images = await comfyui_service.execute_workflow(workflow, timeout=300)
            if images:
                img = images[0].split(",", 1)[1] if images[0].startswith("data:") else images[0]
                path = f"/data/routine/routine-studio-v2/output/fg_{t['name']}.png"
                with open(path, "wb") as f:
                    f.write(base64.b64decode(img))
                print(f"✅ {path}")
        except Exception as e:
            print(f"❌ {e}")

asyncio.run(test())
