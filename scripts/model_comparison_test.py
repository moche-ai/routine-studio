#!/usr/bin/env python3
"""WanVideo 모델 비교 테스트 - high_noise vs low_noise"""

import asyncio
import json
import sys
import shutil
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/data/routine/routine-studio-v2")

from apps.api.services.comfyui import comfyui_service
import random

LOG_FILE = "/data/routine/routine-studio-v2/scripts/model_comparison.log"
RESULT_DIR = Path("/data/comfyui/output/routine/model_comparison")

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# WanVideo I2V 워크플로우 생성 함수
def get_wan_i2v_workflow(
    image_path: str,
    prompt: str,
    model_name: str,  # 모델명 직접 지정
    negative_prompt: str = "blurry, low quality, static, deformed",
    width: int = 832,
    height: int = 480,
    num_frames: int = 41,
    steps: int = 30,
    cfg: float = 6.0,
    seed: int = -1,
    noise_aug: float = 0.0,
    shift: float = 5.0,
):
    if seed == -1:
        seed = random.randint(0, 2**63 - 1)
    
    return {
        "1": {
            "class_type": "WanVideoModelLoader",
            "inputs": {
                "model": model_name,
                "base_precision": "bf16",
                "quantization": "disabled",
                "load_device": "offload_device"
            }
        },
        "2": {
            "class_type": "WanVideoVAELoader",
            "inputs": {
                "model_name": "wan_2.2_vae.safetensors",
                "precision": "bf16"
            }
        },
        "3": {
            "class_type": "LoadWanVideoT5TextEncoder",
            "inputs": {
                "model_name": "umt5-xxl-enc-bf16.safetensors",
                "precision": "bf16",
                "load_device": "offload_device"
            }
        },
        "4": {
            "class_type": "CLIPVisionLoader",
            "inputs": {
                "clip_name": "clip_vision_h.safetensors"
            }
        },
        "5": {
            "class_type": "LoadImage",
            "inputs": {
                "image": image_path
            }
        },
        "6": {
            "class_type": "ImageResizeKJ",
            "inputs": {
                "image": ["5", 0],
                "width": width,
                "height": height,
                "upscale_method": "lanczos",
                "keep_proportion": True,
                "divisible_by": 16
            }
        },
        "7": {
            "class_type": "WanVideoTextEncode",
            "inputs": {
                "positive_prompt": prompt,
                "negative_prompt": negative_prompt,
                "t5": ["3", 0],
                "force_offload": True
            }
        },
        "8": {
            "class_type": "WanVideoClipVisionEncode",
            "inputs": {
                "clip_vision": ["4", 0],
                "image_1": ["6", 0],
                "strength_1": 1.0,
                "strength_2": 1.0,
                "crop": "center",
                "combine_embeds": "average",
                "force_offload": True
            }
        },
        "9": {
            "class_type": "WanVideoImageToVideoEncode",
            "inputs": {
                "width": width,
                "height": height,
                "num_frames": num_frames,
                "noise_aug_strength": noise_aug,
                "start_latent_strength": 1.0,
                "end_latent_strength": 1.0,
                "force_offload": True,
                "vae": ["2", 0],
                "clip_embeds": ["8", 0],
                "start_image": ["6", 0]
            }
        },
        "10": {
            "class_type": "WanVideoSampler",
            "inputs": {
                "model": ["1", 0],
                "image_embeds": ["9", 0],
                "steps": steps,
                "cfg": cfg,
                "shift": shift,
                "seed": seed,
                "force_offload": True,
                "scheduler": "unipc",
                "riflex_freq_index": 0,
                "text_embeds": ["7", 0]
            }
        },
        "11": {
            "class_type": "WanVideoDecode",
            "inputs": {
                "enable_vae_tiling": True,
                "tile_x": 256,
                "tile_y": 256,
                "tile_stride_x": 128,
                "tile_stride_y": 128,
                "samples": ["10", 0],
                "vae": ["2", 0]
            }
        },
        "12": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["11", 0],
                "frame_rate": 24.0,
                "loop_count": 0,
                "filename_prefix": "model_test",
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
                "pix_fmt": "yuv420p",
                "crf": 19,
                "save_metadata": True,
                "trim_to_audio": False
            }
        }
    }

# 테스트 설정
TEST_CONFIGS = [
    # 모델 비교
    {"id": "high_noise_default", "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "noise_aug": 0.0, "cfg": 6.0, "steps": 30, "shift": 5.0},
    {"id": "low_noise_default", "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "noise_aug": 0.0, "cfg": 6.0, "steps": 30, "shift": 5.0},
    
    # low_noise 모델로 파라미터 튜닝
    {"id": "low_noise_aug02", "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "noise_aug": 0.2, "cfg": 6.0, "steps": 30, "shift": 5.0},
    {"id": "low_noise_cfg4", "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "noise_aug": 0.0, "cfg": 4.0, "steps": 30, "shift": 5.0},
    {"id": "low_noise_cfg8", "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "noise_aug": 0.0, "cfg": 8.0, "steps": 30, "shift": 5.0},
    {"id": "low_noise_shift3", "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "noise_aug": 0.0, "cfg": 6.0, "steps": 30, "shift": 3.0},
    {"id": "low_noise_shift8", "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "noise_aug": 0.0, "cfg": 6.0, "steps": 30, "shift": 8.0},
    {"id": "low_noise_steps40", "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "noise_aug": 0.0, "cfg": 6.0, "steps": 40, "shift": 5.0},
    
    # Animate 모델 테스트
    {"id": "animate_default", "model": "wan2.2_animate_14B_bf16.safetensors", "noise_aug": 0.0, "cfg": 6.0, "steps": 30, "shift": 5.0},
    {"id": "animate_cfg4", "model": "wan2.2_animate_14B_bf16.safetensors", "noise_aug": 0.0, "cfg": 4.0, "steps": 30, "shift": 5.0},
    
    # high_noise + noise_aug 조합
    {"id": "high_noise_aug01", "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "noise_aug": 0.1, "cfg": 6.0, "steps": 30, "shift": 5.0},
    {"id": "high_noise_cfg4", "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "noise_aug": 0.0, "cfg": 4.0, "steps": 30, "shift": 5.0},
]

VIDEO_PROMPTS = [
    "cartoon character standing still, subtle breathing animation, gentle eye blinks, soft head movement, calm idle animation",
    "illustrated character with minimal motion, slight breathing, occasional blink, peaceful expression",
]

async def run_test():
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = RESULT_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    log("=" * 70)
    log("🔬 WanVideo 모델 비교 테스트 시작")
    log(f"세션: {session_id}")
    log(f"테스트 수: {len(TEST_CONFIGS)}")
    log("=" * 70)
    
    results = []
    test_image = "routine_test_video.png"
    prompt = VIDEO_PROMPTS[0]
    
    for i, config in enumerate(TEST_CONFIGS, 1):
        log(f"\n[{i}/{len(TEST_CONFIGS)}] {config['id']}")
        log(f"  모델: {config['model'].split('_')[2]}_{config['model'].split('_')[3]}")
        log(f"  noise_aug={config['noise_aug']}, cfg={config['cfg']}, steps={config['steps']}, shift={config['shift']}")
        
        workflow = get_wan_i2v_workflow(
            image_path=test_image,
            prompt=prompt,
            model_name=config["model"],
            noise_aug=config["noise_aug"],
            cfg=config["cfg"],
            steps=config["steps"],
            shift=config["shift"],
            num_frames=41,
        )
        
        try:
            result = await comfyui_service.execute_workflow(workflow)
            
            # 비디오 복사
            output_files = list(Path("/data/comfyui/output").glob("model_test_*.mp4"))
            if output_files:
                latest = max(output_files, key=lambda p: p.stat().st_mtime)
                dest = session_dir / f"{config['id']}.mp4"
                shutil.copy(latest, dest)
                
                # 첫 프레임 추출해서 품질 체크
                import subprocess
                frame_path = session_dir / f"{config['id']}_frame.png"
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(dest),
                    "-vf", "select=eq(n\,0)", "-vframes", "1",
                    str(frame_path)
                ], capture_output=True)
            
            log(f"  ✅ 성공")
            results.append({"id": config["id"], "success": True, "config": config})
        except Exception as e:
            log(f"  ❌ 실패: {e}")
            results.append({"id": config["id"], "success": False, "error": str(e), "config": config})
        
        await asyncio.sleep(5)  # GPU 휴식
    
    # 결과 요약
    log("\n" + "=" * 70)
    log("📊 테스트 결과")
    log("=" * 70)
    
    success_count = sum(1 for r in results if r["success"])
    log(f"성공: {success_count}/{len(results)}")
    
    # 프레임 분석
    log("\n프레임 분석:")
    for config in TEST_CONFIGS:
        frame_path = session_dir / f"{config['id']}_frame.png"
        if frame_path.exists():
            try:
                from PIL import Image
                import numpy as np
                img = Image.open(frame_path)
                arr = np.array(img)
                mean_rgb = arr.mean(axis=(0,1))[:3].astype(int)
                white_ratio = np.sum(np.all(arr > 240, axis=2)) / (arr.shape[0] * arr.shape[1]) * 100
                log(f"  {config['id']}: RGB={tuple(mean_rgb)}, 흰색={white_ratio:.1f}%")
            except Exception as e:
                log(f"  {config['id']}: 분석 실패 - {e}")
    
    # 결과 저장
    result_file = session_dir / "results.json"
    with open(result_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    log(f"\n결과 저장: {session_dir}")
    log("🏁 테스트 완료!")

if __name__ == "__main__":
    with open(LOG_FILE, "w") as f:
        f.write("")
    asyncio.run(run_test())
