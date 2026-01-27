#!/usr/bin/env python3
"""종합 이미지/영상 품질 테스트 - 최적 워크플로우 탐색"""

import asyncio
import json
import sys
import os
import shutil
from datetime import datetime
from pathlib import Path
from itertools import product

sys.path.insert(0, "/data/routine/routine-studio-v2")

from agents.image_generator.workflows import get_first_image_workflow, get_wan_i2v_workflow
from apps.api.services.comfyui import comfyui_service

LOG_FILE = "/data/routine/routine-studio-v2/scripts/comprehensive_test.log"
RESULT_DIR = Path("/data/comfyui/output/routine/quality_search")

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ============================================================
# 테스트 변수 정의
# ============================================================

# 이미지 프롬프트 스타일들
IMAGE_PROMPT_STYLES = [
    {
        "id": "worzak_detailed",
        "name": "Worzak 상세",
        "template": "Worzak-style financial cartoon, young Korean male, full body shot from head to toe, simple white background, bold black outlines, flat clean colors, casual outfit with hoodie and jeans, {expression}, {props}, exaggerated cartoon style"
    },
    {
        "id": "simple_cartoon",
        "name": "심플 카툰",
        "template": "simple cartoon illustration, young asian male character, full body, white background, black outlines, flat colors, hoodie and jeans, {expression}, {props}, cute style, clean design"
    },
    {
        "id": "anime_style",
        "name": "애니메이션",
        "template": "anime style illustration, young korean male character, full body shot, clean white background, soft shading, casual hoodie outfit, {expression}, {props}, high quality anime art"
    },
    {
        "id": "minimalist",
        "name": "미니멀리스트",
        "template": "minimalist vector illustration, young man character, full body, pure white background, simple shapes, flat design, hoodie and pants, {expression}, {props}, modern clean style"
    },
    {
        "id": "pixar_style",
        "name": "픽사 스타일",
        "template": "Pixar-style 3D render, young Korean male character, full body shot, soft studio lighting, white background, casual hoodie outfit, {expression}, {props}, cute proportions, high quality render"
    },
]

# 표정/상황 세트
EXPRESSIONS = [
    {"id": "shocked", "expression": "shocked surprised face", "props": "holding empty wallet, money flying away"},
    {"id": "happy", "expression": "happy confident smile", "props": "holding piggy bank with coins"},
    {"id": "worried", "expression": "worried anxious look", "props": "looking at bills and receipts"},
    {"id": "thinking", "expression": "thoughtful pondering expression", "props": "hand on chin, calculator nearby"},
]

# 이미지 생성 파라미터
IMAGE_PARAMS = [
    {"id": "default", "steps": 25, "cfg": 7.0, "width": 832, "height": 480},
    {"id": "high_steps", "steps": 35, "cfg": 7.0, "width": 832, "height": 480},
    {"id": "low_cfg", "steps": 25, "cfg": 5.0, "width": 832, "height": 480},
    {"id": "high_cfg", "steps": 25, "cfg": 9.0, "width": 832, "height": 480},
    {"id": "square", "steps": 25, "cfg": 7.0, "width": 768, "height": 768},
]

# 비디오 프롬프트 스타일
VIDEO_PROMPT_STYLES = [
    {
        "id": "subtle",
        "name": "미세한 움직임",
        "template": "The character stands still with subtle breathing, eyes blink naturally, slight head movement, {action}, slow zoom in, smooth animation, 3 seconds"
    },
    {
        "id": "gentle",
        "name": "부드러운 움직임",
        "template": "gentle character animation, natural breathing motion, soft eye blinks, {action}, parallax camera effect, cinematic, smooth motion"
    },
    {
        "id": "dynamic",
        "name": "다이나믹",
        "template": "dynamic character pose, expressive body language, {action}, camera slowly orbits, professional animation quality"
    },
]

VIDEO_ACTIONS = [
    "money gently floats in the air",
    "coins slowly fall into piggy bank",
    "papers flutter slightly",
    "small sparkle effects around character",
]

# 비디오 생성 파라미터
VIDEO_PARAMS = [
    {"id": "v1_default", "steps": 30, "cfg": 6.0, "frames": 41, "width": 832, "height": 480},
    {"id": "v2_high_steps", "steps": 40, "cfg": 6.0, "frames": 41, "width": 832, "height": 480},
    {"id": "v3_low_cfg", "steps": 30, "cfg": 4.0, "frames": 41, "width": 832, "height": 480},
    {"id": "v4_high_cfg", "steps": 30, "cfg": 8.0, "frames": 41, "width": 832, "height": 480},
    {"id": "v5_more_frames", "steps": 30, "cfg": 6.0, "frames": 61, "width": 832, "height": 480},
    {"id": "v6_balanced", "steps": 35, "cfg": 5.0, "frames": 41, "width": 832, "height": 480},
]

# ============================================================
# 테스트 함수들
# ============================================================

async def test_image(style, expr, params, test_num, session_dir):
    """이미지 생성 테스트"""
    test_id = f"img_{test_num:03d}_{style['id']}_{expr['id']}_{params['id']}"
    log(f"  [{test_num}] 이미지 테스트: {style['name']} + {expr['id']} + {params['id']}")
    
    prompt = style["template"].format(
        expression=expr["expression"],
        props=expr["props"]
    )
    
    workflow = get_first_image_workflow(
        prompt=prompt,
        width=params["width"],
        height=params["height"],
        steps=params["steps"],
        cfg=params["cfg"]
    )
    
    try:
        result = await comfyui_service.execute_workflow(workflow)
        
        # 결과 이미지 복사
        output_files = list(Path("/data/comfyui/output").glob("ComfyUI_*.png"))
        if output_files:
            latest = max(output_files, key=lambda p: p.stat().st_mtime)
            dest = session_dir / f"{test_id}.png"
            shutil.copy(latest, dest)
            
            # 비디오 테스트용으로 input 폴더에도 복사
            input_copy = Path(f"/data/comfyui/input/{test_id}.png")
            shutil.copy(latest, input_copy)
        
        log(f"      ✅ 성공")
        return {
            "test_id": test_id,
            "success": True,
            "style": style["id"],
            "expression": expr["id"],
            "params": params["id"],
            "prompt": prompt,
            "image_file": str(dest) if output_files else None
        }
    except Exception as e:
        log(f"      ❌ 실패: {e}")
        return {
            "test_id": test_id,
            "success": False,
            "error": str(e)
        }

async def test_video(image_path, video_style, action, params, test_num, session_dir):
    """비디오 생성 테스트"""
    test_id = f"vid_{test_num:03d}_{video_style['id']}_{params['id']}"
    log(f"  [{test_num}] 비디오 테스트: {video_style['name']} + {params['id']}")
    
    prompt = video_style["template"].format(action=action)
    
    workflow = get_wan_i2v_workflow(
        image_path=image_path,
        prompt=prompt,
        width=params["width"],
        height=params["height"],
        num_frames=params["frames"],
        steps=params["steps"],
        cfg=params["cfg"]
    )
    
    try:
        result = await comfyui_service.execute_workflow(workflow)
        
        # 결과 비디오 복사
        output_files = list(Path("/data/comfyui/output").glob("routine_video_*.mp4"))
        if output_files:
            latest = max(output_files, key=lambda p: p.stat().st_mtime)
            dest = session_dir / f"{test_id}.mp4"
            shutil.copy(latest, dest)
        
        log(f"      ✅ 성공")
        return {
            "test_id": test_id,
            "success": True,
            "style": video_style["id"],
            "params": params["id"],
            "prompt": prompt,
            "video_file": str(dest) if output_files else None
        }
    except Exception as e:
        log(f"      ❌ 실패: {e}")
        return {
            "test_id": test_id,
            "success": False,
            "error": str(e)
        }

async def run_comprehensive_test():
    """종합 테스트 실행"""
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = RESULT_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    log("=" * 70)
    log("🔬 종합 이미지/영상 품질 테스트 시작")
    log(f"세션: {session_id}")
    log(f"출력 디렉토리: {session_dir}")
    log("=" * 70)
    
    all_results = {
        "session_id": session_id,
        "image_tests": [],
        "video_tests": [],
        "best_image": None,
        "best_video": None,
    }
    
    # ========================================
    # 1단계: 이미지 프롬프트 스타일 테스트 (20개)
    # ========================================
    log("\n" + "=" * 50)
    log("[1단계] 이미지 프롬프트 스타일 테스트")
    log("=" * 50)
    
    img_test_num = 0
    # 각 스타일 x 첫 번째 표정 x 기본 파라미터
    for style in IMAGE_PROMPT_STYLES:
        for expr in EXPRESSIONS[:2]:  # 2개 표정만
            for params in IMAGE_PARAMS[:2]:  # 2개 파라미터만
                img_test_num += 1
                result = await test_image(style, expr, params, img_test_num, session_dir)
                all_results["image_tests"].append(result)
                await asyncio.sleep(2)  # GPU 휴식
    
    log(f"\n이미지 테스트 완료: {img_test_num}개")
    img_success = sum(1 for r in all_results["image_tests"] if r.get("success"))
    log(f"성공: {img_success}/{img_test_num}")
    
    # 성공한 이미지 중 첫 번째를 비디오 테스트에 사용
    successful_images = [r for r in all_results["image_tests"] if r.get("success") and r.get("image_file")]
    
    if not successful_images:
        log("⚠️ 성공한 이미지가 없어 비디오 테스트 불가")
        # 기존 테스트 이미지 사용
        test_image_for_video = "routine_test_video.png"
    else:
        # 가장 좋은 이미지 선택 (일단 첫 번째)
        best_img = successful_images[0]
        test_image_for_video = f"{best_img['test_id']}.png"
        all_results["best_image"] = best_img
        log(f"비디오 테스트용 이미지: {test_image_for_video}")
    
    # ========================================
    # 2단계: 비디오 파라미터 테스트 (18개)
    # ========================================
    log("\n" + "=" * 50)
    log("[2단계] 비디오 워크플로우 파라미터 테스트")
    log("=" * 50)
    
    vid_test_num = 0
    for video_style in VIDEO_PROMPT_STYLES:
        for params in VIDEO_PARAMS:
            vid_test_num += 1
            action = VIDEO_ACTIONS[vid_test_num % len(VIDEO_ACTIONS)]
            result = await test_video(
                test_image_for_video, 
                video_style, 
                action, 
                params, 
                vid_test_num, 
                session_dir
            )
            all_results["video_tests"].append(result)
            await asyncio.sleep(5)  # 비디오 생성 후 GPU 휴식
    
    log(f"\n비디오 테스트 완료: {vid_test_num}개")
    vid_success = sum(1 for r in all_results["video_tests"] if r.get("success"))
    log(f"성공: {vid_success}/{vid_test_num}")
    
    # ========================================
    # 3단계: 추가 이미지 파라미터 조합 테스트 (10개)
    # ========================================
    log("\n" + "=" * 50)
    log("[3단계] 추가 이미지 파라미터 조합 테스트")
    log("=" * 50)
    
    # 가장 좋은 스타일로 다양한 파라미터 테스트
    best_style = IMAGE_PROMPT_STYLES[0]  # 기본값
    if successful_images:
        best_style_id = successful_images[0]["style"]
        best_style = next((s for s in IMAGE_PROMPT_STYLES if s["id"] == best_style_id), IMAGE_PROMPT_STYLES[0])
    
    for expr in EXPRESSIONS:
        for params in IMAGE_PARAMS[2:]:  # 나머지 파라미터
            img_test_num += 1
            result = await test_image(best_style, expr, params, img_test_num, session_dir)
            all_results["image_tests"].append(result)
            await asyncio.sleep(2)
    
    # ========================================
    # 결과 요약
    # ========================================
    log("\n" + "=" * 70)
    log("📊 테스트 결과 요약")
    log("=" * 70)
    
    total_img = len(all_results["image_tests"])
    total_vid = len(all_results["video_tests"])
    img_success = sum(1 for r in all_results["image_tests"] if r.get("success"))
    vid_success = sum(1 for r in all_results["video_tests"] if r.get("success"))
    
    log(f"총 테스트: {total_img + total_vid}개")
    log(f"  - 이미지: {img_success}/{total_img} 성공")
    log(f"  - 비디오: {vid_success}/{total_vid} 성공")
    
    # 성공한 테스트 분석
    if img_success > 0:
        log("\n성공한 이미지 스타일:")
        style_counts = {}
        for r in all_results["image_tests"]:
            if r.get("success"):
                style = r.get("style", "unknown")
                style_counts[style] = style_counts.get(style, 0) + 1
        for style, count in sorted(style_counts.items(), key=lambda x: -x[1]):
            log(f"  - {style}: {count}개")
    
    if vid_success > 0:
        log("\n성공한 비디오 설정:")
        param_counts = {}
        for r in all_results["video_tests"]:
            if r.get("success"):
                params = r.get("params", "unknown")
                param_counts[params] = param_counts.get(params, 0) + 1
        for params, count in sorted(param_counts.items(), key=lambda x: -x[1]):
            log(f"  - {params}: {count}개")
    
    # 결과 저장
    result_file = session_dir / "test_results.json"
    with open(result_file, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    log(f"\n결과 저장: {result_file}")
    
    # 권장사항 생성
    log("\n" + "=" * 50)
    log("📋 권장사항")
    log("=" * 50)
    
    if vid_success == 0:
        log("⚠️ 비디오 생성 모두 실패 - 워크플로우 근본 수정 필요")
        log("  - WanVideo 노드 스키마 재확인")
        log("  - 모델 호환성 확인")
        log("  - 입력 이미지 포맷/크기 확인")
    elif vid_success < total_vid / 2:
        log("⚠️ 비디오 생성 부분 실패 - 파라미터 튜닝 필요")
    else:
        log("✅ 비디오 생성 대부분 성공")
    
    log("\n🏁 종합 테스트 완료!")
    log(f"결과 확인: {session_dir}")
    
    return all_results

if __name__ == "__main__":
    with open(LOG_FILE, "w") as f:
        f.write("")
    asyncio.run(run_comprehensive_test())
