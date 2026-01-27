#!/usr/bin/env python3
"""듀얼 파이프라인 테스트 - 로컬 vs Gemini 전체 워크플로우 비교"""

import asyncio
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/data/routine/routine-studio-v2")

from apps.api.services.llm import llm_service
from apps.api.services.gemini import gemini_service
from apps.api.services.comfyui import comfyui_service
from agents.image_generator.workflows import get_first_image_workflow, get_wan_i2v_workflow

# 테스트 대본
TEST_SCRIPT = """
월급이 들어오자마자 다 쓰고 있나요?
매달 10만원만 저축해도 1년이면 120만원이에요.
작은 습관이 큰 변화를 만듭니다.
"""

# 캐릭터 설정
CHARACTER_CONFIG = {
    "style": "Worzak-style financial cartoon",
    "description": "young Korean male, full body shot from head to toe, simple white background, bold black outlines, flat clean colors",
    "clothing": "casual outfit with hoodie and jeans"
}

# 결과 디렉토리
RESULT_DIR = Path("/data/comfyui/output/routine/dual_pipeline_test")


class LocalPipeline:
    """로컬 파이프라인 (vLLM + ComfyUI)"""
    
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.results = {"prompts": [], "images": [], "videos": []}
    
    async def generate_prompt(self, script_line: str) -> dict:
        """로컬 LLM으로 프롬프트 생성"""
        system_prompt = f"""너는 유튜브 금융 영상 전문 AI 비주얼 스토리보드 엔지니어야.
        
대본 한 줄을 받으면 다음을 생성해:
1. 이미지 프롬프트 (영어)
2. 영상 프롬프트 (영어)

캐릭터 스타일: {CHARACTER_CONFIG["style"]}
캐릭터 외모: {CHARACTER_CONFIG["description"]}
의상: {CHARACTER_CONFIG["clothing"]}

응답 형식 (JSON만):
{{"image_prompt": "영어 이미지 프롬프트", "video_prompt": "영어 영상 프롬프트"}}"""

        user_prompt = f"대본: {script_line}"
        
        try:
            response = await llm_service.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt
            )
            
            # JSON 파싱
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except Exception as e:
            print(f"  로컬 프롬프트 생성 실패: {e}")
            return {
                "image_prompt": f"cartoon character, {CHARACTER_CONFIG[description]}, expressing emotion about money",
                "video_prompt": "subtle breathing animation, gentle eye blinks, calm idle pose"
            }
    
    async def run(self, script_lines: list) -> dict:
        """전체 파이프라인 실행"""
        print("\n🔧 로컬 파이프라인 시작")
        
        for i, line in enumerate(script_lines, 1):
            print(f"\n  [{i}/{len(script_lines)}] {line[:30]}...")
            
            # 1. 프롬프트 생성
            prompt_data = await self.generate_prompt(line)
            prompt_data["script"] = line
            self.results["prompts"].append(prompt_data)
            print(f"    프롬프트: {prompt_data.get(image_prompt, )[:50]}...")
            
            # 2. 이미지 생성
            try:
                workflow = get_first_image_workflow(
                    prompt=prompt_data.get("image_prompt", ""),
                    width=832,
                    height=480,
                    steps=25,
                    cfg=7.0
                )
                await comfyui_service.execute_workflow(workflow)
                
                # 이미지 복사
                output_files = list(Path("/data/comfyui/output").glob("ComfyUI_*.png"))
                if output_files:
                    latest = max(output_files, key=lambda p: p.stat().st_mtime)
                    dest = self.session_dir / f"local_img_{i:02d}.png"
                    shutil.copy(latest, dest)
                    
                    # input 폴더에도 복사 (비디오용)
                    input_copy = Path(f"/data/comfyui/input/local_img_{i:02d}.png")
                    shutil.copy(latest, input_copy)
                    
                    self.results["images"].append(str(dest))
                    print(f"    이미지 생성 완료: {dest.name}")
            except Exception as e:
                print(f"    이미지 생성 실패: {e}")
                continue
            
            # 3. 비디오 생성
            try:
                workflow = get_wan_i2v_workflow(
                    image_path=f"local_img_{i:02d}.png",
                    prompt=prompt_data.get("video_prompt", "subtle animation"),
                    steps=30,
                    cfg=5.0,
                    num_frames=41
                )
                await comfyui_service.execute_workflow(workflow)
                
                # 비디오 복사
                output_files = list(Path("/data/comfyui/output").glob("routine_video_*.mp4"))
                if output_files:
                    latest = max(output_files, key=lambda p: p.stat().st_mtime)
                    dest = self.session_dir / f"local_vid_{i:02d}.mp4"
                    shutil.copy(latest, dest)
                    self.results["videos"].append(str(dest))
                    print(f"    비디오 생성 완료: {dest.name}")
            except Exception as e:
                print(f"    비디오 생성 실패: {e}")
        
        return self.results


class GeminiPipeline:
    """Gemini 파이프라인 (Gemini API + ComfyUI)"""
    
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.results = {"prompts": [], "images": [], "videos": []}
    
    async def generate_prompt(self, script_line: str) -> dict:
        """Gemini로 프롬프트 생성"""
        prompt = f"""너는 유튜브 금융 영상 전문 AI 비주얼 스토리보드 엔지니어야.

대본: {script_line}

캐릭터 스타일: {CHARACTER_CONFIG["style"]}
캐릭터 외모: {CHARACTER_CONFIG["description"]}
의상: {CHARACTER_CONFIG["clothing"]}

위 대본에 맞는 이미지 프롬프트와 영상 프롬프트를 생성해줘.
- 이미지 프롬프트는 캐릭터의 표정과 포즈가 대본 내용을 표현해야 함
- 영상 프롬프트는 미세한 움직임 (호흡, 눈 깜빡임) 위주

JSON만 응답해줘:
{{"image_prompt": "영어 이미지 프롬프트", "video_prompt": "영어 영상 프롬프트"}}"""

        try:
            response = gemini_service.client.models.generate_content(
                model=gemini_service.model,
                contents=[prompt]
            )
            
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            print(f"  Gemini 프롬프트 생성 실패: {e}")
            return {
                "image_prompt": f"cartoon character, {CHARACTER_CONFIG[description]}, expressing emotion about money",
                "video_prompt": "subtle breathing animation, gentle eye blinks, calm idle pose"
            }
    
    async def run(self, script_lines: list) -> dict:
        """전체 파이프라인 실행"""
        print("\n🤖 Gemini 파이프라인 시작")
        
        for i, line in enumerate(script_lines, 1):
            print(f"\n  [{i}/{len(script_lines)}] {line[:30]}...")
            
            # 1. 프롬프트 생성 (Gemini)
            prompt_data = await self.generate_prompt(line)
            prompt_data["script"] = line
            self.results["prompts"].append(prompt_data)
            print(f"    프롬프트: {prompt_data.get(image_prompt, )[:50]}...")
            
            # 2. 이미지 생성 (ComfyUI - 동일)
            try:
                workflow = get_first_image_workflow(
                    prompt=prompt_data.get("image_prompt", ""),
                    width=832,
                    height=480,
                    steps=25,
                    cfg=7.0
                )
                await comfyui_service.execute_workflow(workflow)
                
                output_files = list(Path("/data/comfyui/output").glob("ComfyUI_*.png"))
                if output_files:
                    latest = max(output_files, key=lambda p: p.stat().st_mtime)
                    dest = self.session_dir / f"gemini_img_{i:02d}.png"
                    shutil.copy(latest, dest)
                    
                    input_copy = Path(f"/data/comfyui/input/gemini_img_{i:02d}.png")
                    shutil.copy(latest, input_copy)
                    
                    self.results["images"].append(str(dest))
                    print(f"    이미지 생성 완료: {dest.name}")
            except Exception as e:
                print(f"    이미지 생성 실패: {e}")
                continue
            
            # 3. 비디오 생성 (ComfyUI - 동일)
            try:
                workflow = get_wan_i2v_workflow(
                    image_path=f"gemini_img_{i:02d}.png",
                    prompt=prompt_data.get("video_prompt", "subtle animation"),
                    steps=30,
                    cfg=5.0,
                    num_frames=41
                )
                await comfyui_service.execute_workflow(workflow)
                
                output_files = list(Path("/data/comfyui/output").glob("routine_video_*.mp4"))
                if output_files:
                    latest = max(output_files, key=lambda p: p.stat().st_mtime)
                    dest = self.session_dir / f"gemini_vid_{i:02d}.mp4"
                    shutil.copy(latest, dest)
                    self.results["videos"].append(str(dest))
                    print(f"    비디오 생성 완료: {dest.name}")
            except Exception as e:
                print(f"    비디오 생성 실패: {e}")
        
        return self.results


async def compare_results(local_results: dict, gemini_results: dict, session_dir: Path):
    """결과 비교 (Gemini로 분석)"""
    print("\n" + "="*60)
    print("📊 결과 비교 분석 (Gemini)")
    print("="*60)
    
    from PIL import Image
    import numpy as np
    
    comparison = {
        "local": {"image_scores": [], "video_scores": []},
        "gemini": {"image_scores": [], "video_scores": []},
        "winner": None
    }
    
    # 이미지 비교
    print("\n📷 이미지 비교:")
    for i in range(min(len(local_results["images"]), len(gemini_results["images"]))):
        local_img = local_results["images"][i]
        gemini_img = gemini_results["images"][i]
        
        # 로컬 분석
        for label, path in [("로컬", local_img), ("Gemini", gemini_img)]:
            img = Image.open(path)
            arr = np.array(img)
            white_ratio = np.sum(np.all(arr > 240, axis=2)) / (arr.shape[0] * arr.shape[1]) * 100
            color_std = arr.std()
            score = min(10, max(1, 10 - white_ratio/10 + color_std/20))
            
            if label == "로컬":
                comparison["local"]["image_scores"].append(score)
            else:
                comparison["gemini"]["image_scores"].append(score)
            
            print(f"  {label} 이미지 {i+1}: 점수={score:.1f}, 흰색={white_ratio:.1f}%")
    
    # 비디오 비교
    print("\n🎬 비디오 비교:")
    for i in range(min(len(local_results["videos"]), len(gemini_results["videos"]))):
        local_vid = local_results["videos"][i]
        gemini_vid = gemini_results["videos"][i]
        
        for label, path in [("로컬", local_vid), ("Gemini", gemini_vid)]:
            # 프레임 추출 및 분석
            import subprocess
            import tempfile
            
            with tempfile.TemporaryDirectory() as tmpdir:
                subprocess.run([
                    "ffmpeg", "-i", path,
                    "-vf", "select=not(mod(n\\,10))",
                    "-vframes", "3",
                    "-vsync", "vfr",
                    f"{tmpdir}/frame_%02d.png"
                ], capture_output=True)
                
                white_ratios = []
                for frame in Path(tmpdir).glob("frame_*.png"):
                    img = Image.open(frame)
                    arr = np.array(img)
                    white_ratio = np.sum(np.all(arr > 240, axis=2)) / (arr.shape[0] * arr.shape[1]) * 100
                    white_ratios.append(white_ratio)
                
                if white_ratios:
                    avg_white = sum(white_ratios) / len(white_ratios)
                    score = max(1, 10 - avg_white/10)
                else:
                    score = 5
                
                if label == "로컬":
                    comparison["local"]["video_scores"].append(score)
                else:
                    comparison["gemini"]["video_scores"].append(score)
                
                print(f"  {label} 비디오 {i+1}: 점수={score:.1f}, 평균 흰색={avg_white:.1f}%")
    
    # 최종 비교
    local_avg = (sum(comparison["local"]["image_scores"]) + sum(comparison["local"]["video_scores"])) / \
                (len(comparison["local"]["image_scores"]) + len(comparison["local"]["video_scores"]) + 0.001)
    gemini_avg = (sum(comparison["gemini"]["image_scores"]) + sum(comparison["gemini"]["video_scores"])) / \
                 (len(comparison["gemini"]["image_scores"]) + len(comparison["gemini"]["video_scores"]) + 0.001)
    
    print("\n" + "="*60)
    print("🏆 최종 결과")
    print("="*60)
    print(f"로컬 파이프라인 평균: {local_avg:.1f}/10")
    print(f"Gemini 파이프라인 평균: {gemini_avg:.1f}/10")
    
    if local_avg > gemini_avg:
        comparison["winner"] = "local"
        print("\n✅ 승자: 로컬 파이프라인")
    elif gemini_avg > local_avg:
        comparison["winner"] = "gemini"
        print("\n✅ 승자: Gemini 파이프라인")
    else:
        comparison["winner"] = "tie"
        print("\n🤝 동점")
    
    # 결과 저장
    result_file = session_dir / "comparison_results.json"
    with open(result_file, "w") as f:
        json.dump({
            "local": local_results,
            "gemini": gemini_results,
            "comparison": comparison
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n결과 저장: {result_file}")
    return comparison


async def main():
    print("="*60)
    print("🔄 듀얼 파이프라인 테스트")
    print("로컬 (vLLM) vs Gemini API 비교")
    print("="*60)
    
    # 세션 디렉토리 생성
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = RESULT_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n결과 디렉토리: {session_dir}")
    
    # 대본 파싱
    script_lines = [line.strip() for line in TEST_SCRIPT.strip().split("\n") if line.strip()]
    print(f"테스트 대본: {len(script_lines)}줄")
    
    # 1. 로컬 파이프라인 실행
    local_pipeline = LocalPipeline(session_dir)
    local_results = await local_pipeline.run(script_lines)
    
    # 2. Gemini 파이프라인 실행
    gemini_pipeline = GeminiPipeline(session_dir)
    gemini_results = await gemini_pipeline.run(script_lines)
    
    # 3. 결과 비교
    await compare_results(local_results, gemini_results, session_dir)
    
    print("\n🏁 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
