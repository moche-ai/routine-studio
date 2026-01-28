#!/usr/bin/env python3
"""
카툰 스타일 유지 + 품질 테스트
- 입력: 라인아트 카툰 이미지
- 목표: Family Guy/나노바나나 스타일 유지, 엉뚱한 이미지 방지
"""

import asyncio
import sys
import base64
from pathlib import Path
from datetime import datetime

sys.path.append("/data/routine/routine-studio-v2")

from apps.api.services.comfyui import comfyui_service
from apps.api.services.workflow import workflow_service

TEST_IMAGE = "/data/routine/routine-studio-v2/test_images/test_face.png"
OUTPUT_DIR = Path("/data/routine/routine-studio-v2/output")

async def load_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

async def save_image(img_data: str, name: str) -> str:
    if img_data.startswith("data:"):
        img_data = img_data.split(",", 1)[1]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"{name}_{timestamp}.png"

    with open(output_path, "wb") as f:
        f.write(base64.b64decode(img_data))

    print(f"  저장: {output_path}")
    return str(output_path)

async def test_ipadapter_style_transfer(ref_image: str, prompt: str, weight: float, weight_type: str):
    """IPAdapter 스타일 전이 테스트"""
    print(f"\n[IPAdapter] weight={weight}, type={weight_type}")
    print(f"  프롬프트: {prompt[:50]}...")

    workflow = workflow_service.build_ipadapter_style_transfer(
        positive_prompt=f"solo, 1person, {prompt}",
        reference_image_b64=ref_image,
        style="cartoon",
        ipadapter_weight=weight,
        weight_type=weight_type,
        steps=30,
        cfg=6.0
    )

    try:
        images = await comfyui_service.execute_workflow(workflow, timeout=180)
        if images:
            name = f"ipa_w{int(weight*100)}_{weight_type.replace(' ', '_')[:10]}"
            await save_image(images[0], name)
            return True
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    return False

async def test_character_consistent(ref_image: str, prompt: str, faceid_weight: float):
    """캐릭터 일관성 (FaceID) 테스트"""
    print(f"\n[FaceID] weight={faceid_weight}")
    print(f"  프롬프트: {prompt[:50]}...")

    workflow = workflow_service.build_character_consistent(
        positive_prompt=prompt,
        reference_image_b64=ref_image,
        style="cartoon",
        faceid_weight=faceid_weight,
        steps=30,
        cfg=5.0
    )

    try:
        images = await comfyui_service.execute_workflow(workflow, timeout=180)
        if images:
            name = f"faceid_w{int(faceid_weight*100)}"
            await save_image(images[0], name)
            return True
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    return False

async def main():
    print("="*60)
    print("카툰 스타일 유지 테스트")
    print("="*60)

    # 레퍼런스 이미지 로드
    ref_image = await load_image(TEST_IMAGE)
    print(f"레퍼런스 이미지 로드 완료 ({len(ref_image)} bytes)")

    # 테스트 프롬프트들
    prompts = [
        "cartoon character, standing pose, confident expression, simple background",
        "cartoon character, sitting pose, thoughtful expression, office background",
    ]

    results = {"success": 0, "fail": 0}

    # 테스트 1: IPAdapter weight/type 조합
    print("\n" + "="*60)
    print("테스트 1: IPAdapter 스타일 전이")
    print("="*60)

    weight_configs = [
        (0.7, "style transfer"),
        (0.8, "style transfer precise"),
        (0.9, "strong style transfer"),
    ]

    for weight, wtype in weight_configs:
        if await test_ipadapter_style_transfer(ref_image, prompts[0], weight, wtype):
            results["success"] += 1
        else:
            results["fail"] += 1

    # 테스트 2: FaceID 일관성
    print("\n" + "="*60)
    print("테스트 2: FaceID 캐릭터 일관성")
    print("="*60)

    for faceid_weight in [0.8, 0.9]:
        if await test_character_consistent(ref_image, prompts[1], faceid_weight):
            results["success"] += 1
        else:
            results["fail"] += 1

    # 결과 요약
    print("\n" + "="*60)
    print("테스트 결과")
    print("="*60)
    print(f"성공: {results['success']}, 실패: {results['fail']}")
    print(f"\n출력 이미지: {OUTPUT_DIR}/")

if __name__ == "__main__":
    asyncio.run(main())
