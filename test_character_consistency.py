#!/usr/bin/env python3
"""
캐릭터 일관성 워크플로우 테스트
- IPAdapter FaceID Plus v2 + FaceDetailer
- InstantID + FaceDetailer (선택)
"""

import asyncio
import sys
import base64
from pathlib import Path

sys.path.append("/data/routine/routine-studio-v2")

from apps.api.services.comfyui import comfyui_service
from apps.api.services.workflow import workflow_service

# 테스트용 레퍼런스 이미지 (간단한 얼굴 이미지 URL 또는 로컬 파일)
TEST_IMAGE_PATH = "/data/routine/routine-studio-v2/test_images/test_face.png"

async def load_test_image() -> str:
    """테스트 이미지 로드"""
    if Path(TEST_IMAGE_PATH).exists():
        with open(TEST_IMAGE_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    else:
        print(f"테스트 이미지 없음: {TEST_IMAGE_PATH}")
        print("기본 테스트 이미지 생성 중...")
        # 기본 이미지 생성 (텍스트만으로)
        workflow = workflow_service.build_basic_sdxl(
            positive_prompt="solo, 1girl, cartoon style, simple face, white background, front view, portrait",
            checkpoint="NovaCartoonXL_v6.safetensors",
            steps=20,
            cfg=6.0,
            width=512,
            height=512
        )
        images = await comfyui_service.execute_workflow(workflow, timeout=120)
        if images:
            # base64 저장
            img_data = images[0]
            if img_data.startswith("data:"):
                img_data = img_data.split(",", 1)[1]

            # 파일로도 저장
            Path(TEST_IMAGE_PATH).parent.mkdir(parents=True, exist_ok=True)
            with open(TEST_IMAGE_PATH, "wb") as f:
                f.write(base64.b64decode(img_data))
            print(f"테스트 이미지 저장: {TEST_IMAGE_PATH}")
            return img_data
        return None

async def test_faceid_workflow():
    """IPAdapter FaceID Plus v2 테스트"""
    print("\n" + "="*60)
    print("테스트 1: IPAdapter FaceID Plus v2 + FaceDetailer")
    print("="*60)

    ref_image = await load_test_image()
    if not ref_image:
        print("❌ 테스트 이미지 로드 실패")
        return None

    print(f"✅ 레퍼런스 이미지 로드 완료 ({len(ref_image)} bytes)")

    try:
        workflow = workflow_service.build_character_consistent(
            positive_prompt="cartoon character, same face, different pose, side view",
            reference_image_b64=ref_image,
            style="cartoon",
            faceid_weight=0.85,
            steps=30,
            cfg=5.0
        )
        print(f"✅ 워크플로우 빌드 완료 (노드 수: {len(workflow)})")

        print("🔄 이미지 생성 중...")
        images = await comfyui_service.execute_workflow(workflow, timeout=300)

        if images:
            print(f"✅ 이미지 생성 완료: {len(images)}장")

            # 결과 저장
            for i, img in enumerate(images):
                img_data = img.split(",", 1)[1] if img.startswith("data:") else img
                output_path = f"/data/routine/routine-studio-v2/output/test_faceid_{i}.png"
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(img_data))
                print(f"   저장: {output_path}")

            return images
        else:
            print("❌ 이미지 생성 실패")
            return None

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_instantid_workflow():
    """InstantID 테스트 (ControlNet 다운로드 완료 후)"""
    print("\n" + "="*60)
    print("테스트 2: InstantID + FaceDetailer")
    print("="*60)

    # InstantID ControlNet 확인
    cn_path = Path("/data/comfyui/models/controlnet/instantid_controlnet.safetensors")
    if not cn_path.exists() or cn_path.stat().st_size < 2_000_000_000:
        print(f"⏳ InstantID ControlNet 다운로드 중... ({cn_path.stat().st_size / 1e9:.2f}GB / ~2.5GB)")
        return None

    ref_image = await load_test_image()
    if not ref_image:
        print("❌ 테스트 이미지 로드 실패")
        return None

    try:
        workflow = workflow_service.build_character_instantid(
            positive_prompt="cartoon character, same face, different angle, three quarter view",
            reference_image_b64=ref_image,
            style="cartoon",
            instantid_weight=0.8,
            controlnet_strength=0.8,
            steps=28,
            cfg=4.5
        )
        print(f"✅ 워크플로우 빌드 완료 (노드 수: {len(workflow)})")

        print("🔄 이미지 생성 중...")
        images = await comfyui_service.execute_workflow(workflow, timeout=300)

        if images:
            print(f"✅ 이미지 생성 완료: {len(images)}장")

            for i, img in enumerate(images):
                img_data = img.split(",", 1)[1] if img.startswith("data:") else img
                output_path = f"/data/routine/routine-studio-v2/output/test_instantid_{i}.png"
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(img_data))
                print(f"   저장: {output_path}")

            return images
        else:
            print("❌ 이미지 생성 실패")
            return None

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_consistency():
    """일관성 테스트 - 같은 레퍼런스로 여러 이미지 생성"""
    print("\n" + "="*60)
    print("테스트 3: 일관성 검증 (3장 연속 생성)")
    print("="*60)

    ref_image = await load_test_image()
    if not ref_image:
        return None

    prompts = [
        "cartoon character, front view, smiling",
        "cartoon character, side view, serious expression",
        "cartoon character, three quarter view, thinking pose"
    ]

    results = []
    for i, prompt in enumerate(prompts):
        print(f"\n[{i+1}/3] {prompt[:50]}...")
        try:
            workflow = workflow_service.build_character_consistent(
                positive_prompt=prompt,
                reference_image_b64=ref_image,
                style="cartoon",
                faceid_weight=0.9,  # 일관성 높이기
                steps=30
            )

            images = await comfyui_service.execute_workflow(workflow, timeout=300)
            if images:
                img_data = images[0].split(",", 1)[1] if images[0].startswith("data:") else images[0]
                output_path = f"/data/routine/routine-studio-v2/output/test_consistency_{i}.png"
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(img_data))
                print(f"   ✅ 저장: {output_path}")
                results.append(output_path)
            else:
                print(f"   ❌ 생성 실패")
        except Exception as e:
            print(f"   ❌ 오류: {e}")

    print(f"\n✅ 일관성 테스트 완료: {len(results)}/3 성공")
    return results

async def main():
    print("="*60)
    print("캐릭터 일관성 워크플로우 테스트")
    print("="*60)

    # 워크플로우 목록 확인
    workflow_service.reload()
    print(f"사용 가능한 워크플로우: {workflow_service.get_workflow_names()}")

    # 테스트 1: IPAdapter FaceID
    result1 = await test_faceid_workflow()

    # 테스트 2: InstantID (다운로드 완료 시)
    result2 = await test_instantid_workflow()

    # 테스트 3: 일관성 검증
    result3 = await test_consistency()

    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)
    print(f"IPAdapter FaceID: {'✅ 성공' if result1 else '❌ 실패'}")
    print(f"InstantID: {'✅ 성공' if result2 else '⏳ 대기 (다운로드 중)'}")
    print(f"일관성 검증: {'✅ 성공' if result3 else '❌ 실패'}")
    print("\n결과 이미지: /data/routine/routine-studio-v2/output/test_*.png")

if __name__ == "__main__":
    asyncio.run(main())
