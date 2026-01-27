#!/usr/bin/env python3
"""퀄리티 체커 테스트 - 로컬 vs Gemini 비교"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, "/data/routine/routine-studio-v2")

from agents.quality_checker.agent import QualityCheckerAgent, CheckerMode

# 테스트할 파일들
TEST_IMAGES = list(Path("/data/comfyui/output/routine/quality_search/20260127_034216").glob("img_*.png"))[:3]
TEST_VIDEOS = list(Path("/data/comfyui/output/routine/model_comparison/20260127_120427").glob("*.mp4"))[:3]

async def test_local():
    """로컬 체커 테스트"""
    print("\n" + "="*60)
    print("🔧 로컬 퀄리티 체커 테스트")
    print("="*60)
    
    checker = QualityCheckerAgent(mode=CheckerMode.LOCAL)
    
    # 이미지 테스트
    print("\n📷 이미지 분석:")
    for img_path in TEST_IMAGES:
        result = await checker.check_image(str(img_path))
        print(f"\n  {img_path.name}:")
        print(f"    점수: {result.get(overall_score, N/A)}/10")
        print(f"    요약: {result.get(summary, N/A)}")
        if result.get("issues"):
            print(f"    문제점: {, .join(result[issues][:2])}")
    
    # 비디오 테스트
    print("\n🎬 비디오 분석:")
    for vid_path in TEST_VIDEOS:
        result = await checker.check_video(str(vid_path))
        print(f"\n  {vid_path.name}:")
        print(f"    점수: {result.get(overall_score, N/A)}/10")
        print(f"    요약: {result.get(summary, N/A)}")
        if result.get("issues"):
            print(f"    문제점: {, .join(result[issues][:2])}")

async def test_gemini():
    """Gemini 체커 테스트"""
    print("\n" + "="*60)
    print("🤖 Gemini 퀄리티 체커 테스트")
    print("="*60)
    
    checker = QualityCheckerAgent(mode=CheckerMode.GEMINI)
    
    # 이미지 테스트 (첫 번째만)
    if TEST_IMAGES:
        print("\n📷 이미지 분석 (Gemini):")
        img_path = TEST_IMAGES[0]
        result = await checker.check_image(str(img_path))
        print(f"\n  {img_path.name}:")
        print(f"    결과: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")
    
    # 비디오 테스트 (첫 번째만)
    if TEST_VIDEOS:
        print("\n🎬 비디오 분석 (Gemini):")
        vid_path = TEST_VIDEOS[0]
        result = await checker.check_video(str(vid_path))
        print(f"\n  {vid_path.name}:")
        print(f"    결과: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")

async def test_comparison():
    """로컬 vs Gemini 비교"""
    print("\n" + "="*60)
    print("📊 로컬 vs Gemini 비교")
    print("="*60)
    
    if not TEST_VIDEOS:
        print("비교할 비디오 없음")
        return
    
    vid_path = str(TEST_VIDEOS[0])
    
    # 로컬 분석
    local_checker = QualityCheckerAgent(mode=CheckerMode.LOCAL)
    local_result = await local_checker.check_video(vid_path)
    
    # Gemini 분석
    gemini_checker = QualityCheckerAgent(mode=CheckerMode.GEMINI)
    gemini_result = await gemini_checker.check_video(vid_path)
    
    print(f"\n비디오: {Path(vid_path).name}")
    print(f"\n로컬 분석:")
    print(f"  점수: {local_result.get(overall_score, N/A)}/10")
    print(f"  문제점: {local_result.get(issues, [])}")
    
    print(f"\nGemini 분석:")
    print(f"  점수: {gemini_result.get(overall_score, N/A)}/10")
    print(f"  요약: {gemini_result.get(summary, N/A)}")

async def main():
    print("🔍 퀄리티 체커 테스트 시작")
    print(f"테스트 이미지: {len(TEST_IMAGES)}개")
    print(f"테스트 비디오: {len(TEST_VIDEOS)}개")
    
    # 1. 로컬 테스트
    await test_local()
    
    # 2. Gemini 테스트
    try:
        await test_gemini()
    except Exception as e:
        print(f"\n⚠️ Gemini 테스트 실패: {e}")
    
    # 3. 비교
    try:
        await test_comparison()
    except Exception as e:
        print(f"\n⚠️ 비교 테스트 실패: {e}")
    
    print("\n✅ 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
