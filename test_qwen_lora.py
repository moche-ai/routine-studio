#!/usr/bin/env python3
"""Qwen Edit + LoRA 테스트"""

import asyncio
import sys
import base64
import json
import random
from copy import deepcopy

sys.path.append("/data/routine/routine-studio-v2")

from apps.api.services.comfyui import comfyui_service

async def test():
    # 레퍼런스 이미지 로드
    with open("/data/routine/routine-studio-v2/test_images/family_guy_ref2.b64", "r") as f:
        ref_b64 = f.read().strip()
    
    print(f"이미지 로드: {len(ref_b64)} bytes")
    
    # 워크플로우 로드
    with open("/data/routine/routine-studio-v2/workflows/v2/qwen_edit_with_lora.json", "r") as f:
        template = json.load(f)
    
    # 테스트 설정
    tests = [
        {
            "name": "lora_d50",
            "instruction": "Transform into an Asian man with black hair, wearing glasses and a bright RED suit jacket. Keep cartoon style.",
            "denoise": 0.50,
            "lora_strength": 0.9,
            "steps": 30,
            "cfg": 5.0
        },
        {
            "name": "lora_d60",
            "instruction": "Transform into an Asian man with black hair, wearing glasses and a bright RED suit jacket. Keep cartoon style.",
            "denoise": 0.60,
            "lora_strength": 0.9,
            "steps": 30,
            "cfg": 5.0
        },
        {
            "name": "lora_d70",
            "instruction": "Transform into an Asian man with black hair, wearing glasses and a bright RED suit jacket. Keep cartoon style.",
            "denoise": 0.70,
            "lora_strength": 0.9,
            "steps": 30,
            "cfg": 5.0
        },
    ]
    
    for t in tests:
        print(f"\n테스트: {t['name']} (denoise={t['denoise']})")
        
        # 워크플로우 복사 및 변수 치환
        workflow = deepcopy(template["workflow"])
        
        # 변수 치환
        workflow["1"]["inputs"]["image"] = ref_b64
        workflow["5"]["inputs"]["strength_model"] = t["lora_strength"]
        workflow["6"]["inputs"]["prompt"] = t["instruction"]
        workflow["8"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        workflow["8"]["inputs"]["steps"] = t["steps"]
        workflow["8"]["inputs"]["cfg"] = t["cfg"]
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
            else:
                print("❌ 이미지 생성 실패")
        except Exception as e:
            print(f"❌ 오류: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(test())
