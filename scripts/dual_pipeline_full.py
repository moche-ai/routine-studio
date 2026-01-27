#!/usr/bin/env python3
"""듀얼 파이프라인 테스트 - 로컬 vs Gemini 프롬프트 품질 비교
로컬: vLLM (프롬프트) + ComfyUI (이미지/비디오)
Gemini: Gemini API (프롬프트) + ComfyUI (이미지/비디오)

Note: Imagen 쿼터 제한으로 이미지 생성은 둘 다 ComfyUI 사용
프롬프트 생성 품질 비교가 핵심
"""

import asyncio
import sys
import json
import shutil
import base64
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/data/routine/routine-studio-v2")

from google import genai
from PIL import Image
import numpy as np
from io import BytesIO

from apps.api.services.llm import llm_service
from apps.api.services.comfyui import comfyui_service
from agents.image_generator.workflows import get_first_image_workflow, get_wan_i2v_workflow

# API 키
GEMINI_API_KEY = "AIzaSyDWMMQPoQNTnSS0EwGVYJSNPUaM-PBK1UA"

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
RESULT_DIR = Path("/data/comfyui/output/routine/dual_pipeline_full")


def save_base64_image(base64_str: str, output_path: str):
    """Base64 이미지를 파일로 저장"""
    # Remove data URI prefix if present
    if base64_str.startswith("data:"):
        base64_str = base64_str.split(",", 1)[1]

    img_data = base64.b64decode(base64_str)
    with open(output_path, "wb") as f:
        f.write(img_data)


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

            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            return json.loads(response.strip())
        except Exception as e:
            print(f"  로컬 프롬프트 생성 실패: {e}")
            return {
                "image_prompt": f"cartoon character, {CHARACTER_CONFIG['description']}, expressing emotion about money",
                "video_prompt": "subtle breathing animation, gentle eye blinks, calm idle pose"
            }

    async def run(self, script_lines: list) -> dict:
        """전체 파이프라인 실행"""
        print("\n" + "=" * 60)
        print("🔧 로컬 파이프라인 (vLLM + ComfyUI)")
        print("=" * 60)

        for i, line in enumerate(script_lines, 1):
            print(f"\n  [{i}/{len(script_lines)}] {line[:30]}...")

            # 1. 프롬프트 생성
            prompt_data = await self.generate_prompt(line)
            prompt_data["script"] = line
            self.results["prompts"].append(prompt_data)
            print(f"    프롬프트: {prompt_data.get('image_prompt', '')[:50]}...")

            # 2. 이미지 생성 (ComfyUI)
            try:
                workflow = get_first_image_workflow(
                    prompt=prompt_data.get("image_prompt", ""),
                    width=832,
                    height=480,
                    steps=25,
                    cfg=7.0
                )
                images = await comfyui_service.execute_workflow(workflow)

                if images:
                    # Base64 이미지를 파일로 저장
                    dest = self.session_dir / f"local_img_{i:02d}.png"
                    save_base64_image(images[0], str(dest))

                    # ComfyUI input에도 복사 (비디오 생성용)
                    input_copy = Path(f"/data/comfyui/input/local_img_{i:02d}.png")
                    save_base64_image(images[0], str(input_copy))

                    self.results["images"].append(str(dest))
                    print(f"    ✅ 이미지 생성: {dest.name}")
                else:
                    print(f"    ❌ 이미지 생성 실패: 반환된 이미지 없음")
                    continue
            except Exception as e:
                print(f"    ❌ 이미지 생성 실패: {e}")
                continue

            # 3. 비디오 생성 (ComfyUI WanVideo)
            try:
                workflow = get_wan_i2v_workflow(
                    image_path=f"local_img_{i:02d}.png",
                    prompt=prompt_data.get("video_prompt", "subtle animation"),
                    steps=30,
                    cfg=5.0,
                    num_frames=41
                )
                videos = await comfyui_service.execute_workflow(workflow, timeout=600)

                # 비디오 파일은 ComfyUI output에 남아있음 (base64로 반환되지 않음)
                output_files = list(Path("/data/comfyui/output").glob("routine_video_*.mp4"))
                if output_files:
                    latest = max(output_files, key=lambda p: p.stat().st_mtime)
                    dest = self.session_dir / f"local_vid_{i:02d}.mp4"
                    shutil.copy(latest, dest)
                    self.results["videos"].append(str(dest))
                    print(f"    ✅ 비디오 생성: {dest.name}")
                else:
                    print(f"    ⚠️ 비디오 파일을 찾을 수 없음")
            except Exception as e:
                print(f"    ❌ 비디오 생성 실패: {e}")

        return self.results


class GeminiPipeline:
    """Gemini 파이프라인 (Gemini API 프롬프트 + ComfyUI 이미지/비디오)"""

    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.results = {"prompts": [], "images": [], "videos": []}
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    async def generate_prompt(self, script_line: str) -> dict:
        """Gemini로 프롬프트 생성"""
        prompt = f"""너는 유튜브 금융 영상 전문 AI 비주얼 스토리보드 엔지니어야.

대본: {script_line}

캐릭터 스타일: {CHARACTER_CONFIG["style"]}
캐릭터 외모: {CHARACTER_CONFIG["description"]}
의상: {CHARACTER_CONFIG["clothing"]}

위 대본에 맞는 이미지 프롬프트와 영상 프롬프트를 생성해줘.

🚨 이미지 프롬프트 필수 요구사항:
- 동일한 캐릭터의 전신 샷 (머리부터 발끝까지 완전히 보여야 함)
- 스타일: Worzak-style financial cartoon
- 배경: 흰색 또는 밝은 단색 배경
- 테두리: 굵은 검은색
- 색상: 깔끔하고 평면적
- 대본 내용에 맞는 과장된 얼굴 표정
- 소품은 필요시 최소한으로 (돈, 지폐, 영수증, 달력, 시계, 화살표, 차트)
- 이미지 안에 텍스트 없음

🎬 영상 프롬프트 규칙:
- 전신 캐릭터의 미세하고 자연스러운 움직임
- 허용: 눈 깜빡임, 호흡, 고개 살짝 기울임, 손/팔 작은 움직임
- 소품 애니메이션: 돈 살짝 떠다니기, 달력 넘기기, 시계 바늘 움직임
- 효과: 느린 줌인 또는 부드러운 패럴랙스
- 캐릭터 디자인/의상/비율 일관성 유지

JSON만 응답:
{{"image_prompt": "영어 이미지 프롬프트 (상세하게)", "video_prompt": "영어 영상 프롬프트"}}"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
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
                "image_prompt": f"cartoon character, {CHARACTER_CONFIG['description']}, expressing emotion about money",
                "video_prompt": "subtle breathing animation, gentle eye blinks, calm idle pose"
            }

    async def run(self, script_lines: list) -> dict:
        """전체 파이프라인 실행"""
        print("\n" + "=" * 60)
        print("🤖 Gemini 파이프라인 (Gemini API 프롬프트 + ComfyUI)")
        print("=" * 60)

        for i, line in enumerate(script_lines, 1):
            print(f"\n  [{i}/{len(script_lines)}] {line[:30]}...")

            # 1. 프롬프트 생성 (Gemini)
            prompt_data = await self.generate_prompt(line)
            prompt_data["script"] = line
            self.results["prompts"].append(prompt_data)
            print(f"    프롬프트: {prompt_data.get('image_prompt', '')[:50]}...")

            # 2. 이미지 생성 (ComfyUI)
            try:
                workflow = get_first_image_workflow(
                    prompt=prompt_data.get("image_prompt", ""),
                    width=832,
                    height=480,
                    steps=25,
                    cfg=7.0
                )
                images = await comfyui_service.execute_workflow(workflow)

                if images:
                    # Base64 이미지를 파일로 저장
                    dest = self.session_dir / f"gemini_img_{i:02d}.png"
                    save_base64_image(images[0], str(dest))

                    # ComfyUI input에도 복사 (비디오 생성용)
                    input_copy = Path(f"/data/comfyui/input/gemini_img_{i:02d}.png")
                    save_base64_image(images[0], str(input_copy))

                    self.results["images"].append(str(dest))
                    print(f"    ✅ 이미지 생성: {dest.name}")
                else:
                    print(f"    ❌ 이미지 생성 실패: 반환된 이미지 없음")
                    continue
            except Exception as e:
                print(f"    ❌ 이미지 생성 실패: {e}")
                continue

            # 3. 비디오 생성 (ComfyUI WanVideo)
            try:
                workflow = get_wan_i2v_workflow(
                    image_path=f"gemini_img_{i:02d}.png",
                    prompt=prompt_data.get("video_prompt", "subtle animation"),
                    steps=30,
                    cfg=5.0,
                    num_frames=41
                )
                videos = await comfyui_service.execute_workflow(workflow, timeout=600)

                # 비디오 파일은 ComfyUI output에 남아있음
                output_files = list(Path("/data/comfyui/output").glob("routine_video_*.mp4"))
                if output_files:
                    latest = max(output_files, key=lambda p: p.stat().st_mtime)
                    dest = self.session_dir / f"gemini_vid_{i:02d}.mp4"
                    shutil.copy(latest, dest)
                    self.results["videos"].append(str(dest))
                    print(f"    ✅ 비디오 생성: {dest.name}")
                else:
                    print(f"    ⚠️ 비디오 파일을 찾을 수 없음")
            except Exception as e:
                print(f"    ❌ 비디오 생성 실패: {e}")

        return self.results


def analyze_image(path: str) -> dict:
    """이미지 분석"""
    img = Image.open(path)
    arr = np.array(img)

    white_ratio = np.sum(np.all(arr > 240, axis=2)) / (arr.shape[0] * arr.shape[1]) * 100
    black_ratio = np.sum(np.all(arr < 30, axis=2)) / (arr.shape[0] * arr.shape[1]) * 100
    color_std = arr.std()

    score = min(10, max(1, 10 - white_ratio / 10 + color_std / 30 + black_ratio / 5))

    return {
        "score": round(score, 1),
        "white_ratio": round(white_ratio, 1),
        "black_ratio": round(black_ratio, 1),
        "color_std": round(color_std, 1)
    }


def analyze_video(path: str) -> dict:
    """비디오 분석"""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run([
            "ffmpeg", "-i", path,
            "-vf", "select=not(mod(n\\,10))",
            "-vframes", "4",
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
            score = max(1, 10 - avg_white / 10)
        else:
            avg_white = 100
            score = 1

        return {
            "score": round(score, 1),
            "avg_white_ratio": round(avg_white, 1)
        }


async def compare_results(local_results: dict, gemini_results: dict, session_dir: Path):
    """결과 비교"""
    print("\n" + "=" * 60)
    print("📊 결과 비교 분석")
    print("=" * 60)

    comparison = {
        "local": {"images": [], "videos": []},
        "gemini": {"images": [], "videos": []},
    }

    # 프롬프트 비교
    print("\n📝 프롬프트 비교:")
    print("-" * 40)
    for i in range(max(len(local_results["prompts"]), len(gemini_results["prompts"]))):
        print(f"\n  장면 {i + 1}:")
        if i < len(local_results["prompts"]):
            lp = local_results["prompts"][i]
            print(f"    로컬 프롬프트: {lp.get('image_prompt', '')[:60]}...")
        if i < len(gemini_results["prompts"]):
            gp = gemini_results["prompts"][i]
            print(f"    Gemini 프롬프트: {gp.get('image_prompt', '')[:60]}...")

    # 이미지 비교
    print("\n📷 이미지 비교:")
    print("-" * 40)
    for i in range(max(len(local_results["images"]), len(gemini_results["images"]))):
        print(f"\n  장면 {i + 1}:")

        if i < len(local_results["images"]):
            analysis = analyze_image(local_results["images"][i])
            comparison["local"]["images"].append(analysis)
            print(f"    로컬:  점수={analysis['score']}, 흰색={analysis['white_ratio']}%, 외곽선={analysis['black_ratio']}%")

        if i < len(gemini_results["images"]):
            analysis = analyze_image(gemini_results["images"][i])
            comparison["gemini"]["images"].append(analysis)
            print(f"    Gemini: 점수={analysis['score']}, 흰색={analysis['white_ratio']}%, 외곽선={analysis['black_ratio']}%")

    # 비디오 비교
    print("\n🎬 비디오 비교:")
    print("-" * 40)
    for i in range(max(len(local_results["videos"]), len(gemini_results["videos"]))):
        print(f"\n  장면 {i + 1}:")

        if i < len(local_results["videos"]):
            analysis = analyze_video(local_results["videos"][i])
            comparison["local"]["videos"].append(analysis)
            print(f"    로컬:  점수={analysis['score']}, 평균 흰색={analysis['avg_white_ratio']}%")

        if i < len(gemini_results["videos"]):
            analysis = analyze_video(gemini_results["videos"][i])
            comparison["gemini"]["videos"].append(analysis)
            print(f"    Gemini: 점수={analysis['score']}, 평균 흰색={analysis['avg_white_ratio']}%")

    # 최종 점수 계산
    local_img_avg = sum(a["score"] for a in comparison["local"]["images"]) / max(1, len(comparison["local"]["images"]))
    local_vid_avg = sum(a["score"] for a in comparison["local"]["videos"]) / max(1, len(comparison["local"]["videos"]))
    local_total = (local_img_avg + local_vid_avg) / 2

    gemini_img_avg = sum(a["score"] for a in comparison["gemini"]["images"]) / max(1, len(comparison["gemini"]["images"]))
    gemini_vid_avg = sum(a["score"] for a in comparison["gemini"]["videos"]) / max(1, len(comparison["gemini"]["videos"]))
    gemini_total = (gemini_img_avg + gemini_vid_avg) / 2

    print("\n" + "=" * 60)
    print("🏆 최종 결과")
    print("=" * 60)
    print(f"\n로컬 파이프라인 (vLLM 프롬프트):")
    print(f"  이미지 평균: {local_img_avg:.1f}/10")
    print(f"  비디오 평균: {local_vid_avg:.1f}/10")
    print(f"  총점: {local_total:.1f}/10")

    print(f"\nGemini 파이프라인 (Gemini 프롬프트):")
    print(f"  이미지 평균: {gemini_img_avg:.1f}/10")
    print(f"  비디오 평균: {gemini_vid_avg:.1f}/10")
    print(f"  총점: {gemini_total:.1f}/10")

    if local_total > gemini_total:
        winner = "local"
        print(f"\n✅ 승자: 로컬 파이프라인 (+{local_total - gemini_total:.1f}점)")
    elif gemini_total > local_total:
        winner = "gemini"
        print(f"\n✅ 승자: Gemini 파이프라인 (+{gemini_total - local_total:.1f}점)")
    else:
        winner = "tie"
        print("\n🤝 동점")

    # 결과 저장
    full_results = {
        "timestamp": datetime.now().isoformat(),
        "note": "프롬프트 생성 품질 비교 (이미지/비디오 생성은 둘 다 ComfyUI)",
        "local": {
            "prompts": local_results["prompts"],
            "images": local_results["images"],
            "videos": local_results["videos"],
            "analysis": comparison["local"]
        },
        "gemini": {
            "prompts": gemini_results["prompts"],
            "images": gemini_results["images"],
            "videos": gemini_results["videos"],
            "analysis": comparison["gemini"]
        },
        "summary": {
            "local_score": round(local_total, 1),
            "gemini_score": round(gemini_total, 1),
            "winner": winner
        }
    }

    result_file = session_dir / "full_comparison.json"
    with open(result_file, "w") as f:
        json.dump(full_results, f, indent=2, ensure_ascii=False)

    print(f"\n📁 결과 저장: {result_file}")
    print(f"📁 생성 파일: {session_dir}")

    return full_results


async def main():
    print("=" * 60)
    print("🔄 듀얼 파이프라인 전체 테스트")
    print("로컬 (vLLM 프롬프트) vs Gemini (Gemini API 프롬프트)")
    print("=" * 60)

    # 세션 디렉토리 생성
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = RESULT_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n결과 디렉토리: {session_dir}")

    # 대본 파싱
    script_lines = [line.strip() for line in TEST_SCRIPT.strip().split("\n") if line.strip()]
    print(f"테스트 대본: {len(script_lines)}줄")
    for i, line in enumerate(script_lines, 1):
        print(f"  {i}. {line}")

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
