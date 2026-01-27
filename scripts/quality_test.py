#!/usr/bin/env python3
"""이미지/영상 품질 검수 및 워크플로우 테스트 스크립트"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/data/routine/routine-studio-v2")

from agents.image_generator.workflows import get_first_image_workflow, get_consistent_image_workflow, get_wan_i2v_workflow
from apps.api.services.comfyui import comfyui_service

# 로그 파일
LOG_FILE = "/data/routine/routine-studio-v2/scripts/quality_test.log"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# 테스트 프롬프트 - 다양한 스타일로 테스트
TEST_PROMPTS = [
    {
        "id": 1,
        "script": "월급이 들어오자마자 다 쓰고 있나요?",
        "image_prompt_v1": "Worzak-style financial cartoon, young Korean male, full body shot from head to toe, simple white background, bold black outlines, flat clean colors, casual outfit with hoodie and jeans, surprised expression looking at empty wallet, money flying away from wallet, exaggerated shocked face",
        "image_prompt_v2": "simple cartoon illustration, young asian male character, full body, white background, black outlines, flat colors, hoodie and jeans, shocked face, holding empty wallet, money bills flying away, cute style, clean design",
        "video_prompt": "The character stands still with subtle breathing, eyes blink naturally, slight head movement showing surprise, money gently floats away, slow zoom in, 3-5 seconds, smooth animation",
    },
    {
        "id": 2, 
        "script": "매달 10만원만 저축해도 1년이면 120만원이에요.",
        "image_prompt_v1": "Worzak-style financial cartoon, young Korean male, full body shot from head to toe, simple white background, bold black outlines, flat clean colors, casual outfit with hoodie and jeans, happy confident smile, holding a piggy bank with coins, encouraging expression",
        "image_prompt_v2": "simple cartoon illustration, young asian male character, full body, white background, black outlines, flat colors, hoodie and jeans, happy smile, holding piggy bank, coins falling in, cute style, clean design",
        "video_prompt": "The character breathing naturally with gentle smile, eyes blink occasionally, coins slowly drop into piggy bank one by one, soft parallax effect, 3-5 seconds, calm animation",
    }
]

# 워크플로우 파라미터 변형 테스트
VIDEO_PARAMS_VARIATIONS = [
    {
        "name": "default",
        "width": 832,
        "height": 480,
        "num_frames": 41,
        "steps": 30,
        "cfg": 6.0,
    },
    {
        "name": "high_steps",
        "width": 832,
        "height": 480,
        "num_frames": 41,
        "steps": 40,
        "cfg": 6.0,
    },
    {
        "name": "lower_cfg",
        "width": 832,
        "height": 480,
        "num_frames": 41,
        "steps": 30,
        "cfg": 4.0,
    },
    {
        "name": "higher_cfg",
        "width": 832,
        "height": 480,
        "num_frames": 41,
        "steps": 30,
        "cfg": 8.0,
    },
]

async def test_image_generation(prompt_data, session_id):
    """이미지 생성 테스트"""
    log(f"=== 이미지 생성 테스트: {prompt_data["id"]} ===")
    
    results = {}
    
    # V1 프롬프트 테스트
    for version in ["v1", "v2"]:
        prompt_key = f"image_prompt_{version}"
        prompt = prompt_data[prompt_key]
        
        log(f"  [{version}] 프롬프트: {prompt[:80]}...")
        
        workflow = get_first_image_workflow(
            prompt=prompt,
            width=832,  # 비디오와 같은 비율로 생성
            height=480,
            steps=25,
            cfg=7.0
        )
        
        try:
            result = await comfyui_service.execute_workflow(workflow)
            results[version] = {"success": True, "result": result}
            log(f"  [{version}] 성공")
        except Exception as e:
            results[version] = {"success": False, "error": str(e)}
            log(f"  [{version}] 실패: {e}")
    
    return results

async def test_video_generation(image_path, prompt_data, params, session_id):
    """비디오 생성 테스트"""
    log(f"=== 비디오 생성 테스트: {params["name"]} ===")
    
    workflow = get_wan_i2v_workflow(
        image_path=image_path,
        prompt=prompt_data["video_prompt"],
        width=params["width"],
        height=params["height"],
        num_frames=params["num_frames"],
        steps=params["steps"],
        cfg=params["cfg"],
    )
    
    try:
        result = await comfyui_service.execute_workflow(workflow)
        log(f"  [{params["name"]}] 성공")
        return {"success": True, "params": params, "result": result}
    except Exception as e:
        log(f"  [{params["name"]}] 실패: {e}")
        return {"success": False, "params": params, "error": str(e)}

async def run_full_test():
    """전체 테스트 실행"""
    log("=" * 60)
    log("이미지/영상 품질 검수 및 워크플로우 테스트 시작")
    log("=" * 60)
    
    test_session = f"quality_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = Path(f"/data/comfyui/output/routine/{test_session}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_results = {
        "session": test_session,
        "image_tests": [],
        "video_tests": [],
        "summary": {}
    }
    
    # 1단계: 이미지 프롬프트 테스트
    log("\n[1단계] 이미지 프롬프트 비교 테스트")
    log("-" * 40)
    
    for prompt_data in TEST_PROMPTS[:1]:  # 첫 번째만 테스트
        img_result = await test_image_generation(prompt_data, test_session)
        all_results["image_tests"].append({
            "prompt_id": prompt_data["id"],
            "results": img_result
        })
    
    # 2단계: 비디오 워크플로우 파라미터 테스트
    log("\n[2단계] 비디오 워크플로우 파라미터 테스트")
    log("-" * 40)
    
    # 테스트용 이미지 사용
    test_image = "routine_test_video.png"  # 기존 테스트 이미지
    
    for params in VIDEO_PARAMS_VARIATIONS:
        vid_result = await test_video_generation(
            test_image, 
            TEST_PROMPTS[0], 
            params, 
            test_session
        )
        all_results["video_tests"].append(vid_result)
        
        # 각 테스트 사이에 잠시 대기 (GPU 메모리 정리)
        await asyncio.sleep(5)
    
    # 결과 요약
    log("\n" + "=" * 60)
    log("테스트 완료 - 결과 요약")
    log("=" * 60)
    
    img_success = sum(1 for t in all_results["image_tests"] 
                      for r in t["results"].values() if r.get("success"))
    img_total = sum(len(t["results"]) for t in all_results["image_tests"])
    
    vid_success = sum(1 for t in all_results["video_tests"] if t.get("success"))
    vid_total = len(all_results["video_tests"])
    
    all_results["summary"] = {
        "image_success_rate": f"{img_success}/{img_total}",
        "video_success_rate": f"{vid_success}/{vid_total}",
    }
    
    log(f"이미지 생성: {img_success}/{img_total} 성공")
    log(f"비디오 생성: {vid_success}/{vid_total} 성공")
    
    # 결과 저장
    result_file = output_dir / "test_results.json"
    with open(result_file, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    log(f"\n결과 저장: {result_file}")
    
    # 분석 및 권장사항
    log("\n[분석 및 권장사항]")
    log("-" * 40)
    
    if vid_success == 0:
        log("⚠️ 모든 비디오 생성 실패 - 워크플로우 근본적 문제 있음")
        log("  - ComfyUI 노드 스키마 재확인 필요")
        log("  - 모델 호환성 확인 필요")
    elif vid_success < vid_total:
        log("⚠️ 일부 비디오 생성 실패 - 파라미터 조정 필요")
        successful_params = [t["params"]["name"] for t in all_results["video_tests"] if t.get("success")]
        log(f"  - 성공한 설정: {successful_params}")
    else:
        log("✅ 모든 비디오 생성 성공")
    
    log("\n테스트 완료!")
    return all_results

if __name__ == "__main__":
    # 로그 파일 초기화
    with open(LOG_FILE, "w") as f:
        f.write("")
    
    asyncio.run(run_full_test())
