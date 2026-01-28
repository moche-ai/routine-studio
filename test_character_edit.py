#!/usr/bin/env python3
"""
Family Guy 캐릭터 -> 동양인 여성 변환 테스트
다양한 워크플로우와 설정값을 테스트
"""
import json
import base64
import requests
import time
import os
from pathlib import Path

COMFY_URL = "http://localhost:8188"

# 테스트 이미지 경로
TEST_IMAGE = "/data/routine/routine-studio-v2/test_images/family_guy_male.png"
OUTPUT_DIR = "/data/routine/routine-studio-v2/test_images/outputs"

def load_image_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def queue_prompt(workflow):
    """ComfyUI에 워크플로우 큐"""
    response = requests.post(
        f"{COMFY_URL}/prompt",
        json={"prompt": workflow}
    )
    return response.json()

def wait_for_completion(prompt_id, timeout=300):
    """완료 대기"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{COMFY_URL}/history/{prompt_id}")
            history = response.json()
            if prompt_id in history:
                return history[prompt_id]
        except:
            pass
        time.sleep(2)
    return None

def test_qwen_edit(image_b64, prompt, denoise=0.75, steps=30, cfg=5.0, test_name="qwen"):
    """Qwen Image Edit 테스트"""
    print(f"\n=== Testing Qwen Edit: {test_name} ===")
    print(f"   denoise={denoise}, steps={steps}, cfg={cfg}")
    
    workflow = {
        "1": {
            "class_type": "ETN_LoadImageBase64",
            "inputs": {"image": image_b64}
        },
        "2": {
            "class_type": "QwenLoader",
            "inputs": {
                "model_name": "Qwen2.5-VL-7B_qwen-image-edit-v1-2511_F16.gguf",
                "text_encoder_name": "Qwen2.5-VL-7B_qwen-image-edit-v1-2511_F16.gguf",
                "vae_name": "ae.safetensors"
            }
        },
        "3": {
            "class_type": "TextEncodeQwenImageEdit",
            "inputs": {
                "qwen_model": ["2", 0],
                "text": prompt,
                "image": ["1", 0]
            }
        },
        "4": {
            "class_type": "EmptyQwenImageLayeredLatentImage",
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            }
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["2", 1],
                "positive": ["3", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": 12345,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": denoise
            }
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["2", 2]
            }
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["6", 0],
                "filename_prefix": f"test_{test_name}"
            }
        }
    }
    
    result = queue_prompt(workflow)
    if "prompt_id" in result:
        print(f"   Queued: {result['prompt_id']}")
        completion = wait_for_completion(result["prompt_id"])
        if completion:
            print(f"   Completed!")
            return True
    return False

def test_uso_style(image_b64, prompt, test_name="uso"):
    """USO Style Reference 테스트"""
    print(f"\n=== Testing USO Style: {test_name} ===")
    
    workflow = {
        # FLUX Dev 로더
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "flux1-dev-Q4_K_S.gguf",
                "weight_dtype": "default"
            }
        },
        # VAE
        "2": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"}
        },
        # CLIP
        "3": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "t5xxl_fp16.safetensors",
                "clip_name2": "clip_l.safetensors",
                "type": "flux"
            }
        },
        # USO Model Patch Loader
        "4": {
            "class_type": "ModelPatchLoader",
            "inputs": {
                "model_patch_name": "uso-flux1-projector-v1.safetensors"
            }
        },
        # CLIP Vision
        "5": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "sigclip_vision_patch14_384.safetensors"}
        },
        # LoRA
        "6": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": "uso-flux1-dit-lora-v1.safetensors",
                "strength_model": 1.0
            }
        },
        # 이미지 로드
        "7": {
            "class_type": "ETN_LoadImageBase64",
            "inputs": {"image": image_b64}
        },
        # CLIP Vision Encode
        "8": {
            "class_type": "CLIPVisionEncode",
            "inputs": {
                "clip_vision": ["5", 0],
                "image": ["7", 0]
            }
        },
        # USO Style Reference 적용
        "9": {
            "class_type": "USOStyleReference",
            "inputs": {
                "model": ["6", 0],
                "model_patch": ["4", 0],
                "clip_vision_output": ["8", 0]
            }
        },
        # Text Encode
        "10": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["3", 0],
                "text": prompt
            }
        },
        # Empty Latent
        "11": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            }
        },
        # Sampler
        "12": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["9", 0],
                "positive": ["10", 0],
                "negative": ["10", 0],
                "latent_image": ["11", 0],
                "seed": 12345,
                "steps": 30,
                "cfg": 3.5,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0
            }
        },
        # VAE Decode
        "13": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["12", 0],
                "vae": ["2", 0]
            }
        },
        # Save
        "14": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["13", 0],
                "filename_prefix": f"test_{test_name}"
            }
        }
    }
    
    result = queue_prompt(workflow)
    if "prompt_id" in result:
        print(f"   Queued: {result['prompt_id']}")
        completion = wait_for_completion(result["prompt_id"])
        if completion:
            print(f"   Completed!")
            return True
    return False

def test_ipadapter(image_b64, prompt, denoise=0.6, strength=0.8, test_name="ipadapter"):
    """IPAdapter 스타일 전이 테스트"""
    print(f"\n=== Testing IPAdapter: {test_name} ===")
    print(f"   denoise={denoise}, strength={strength}")
    
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}
        },
        "2": {
            "class_type": "ETN_LoadImageBase64",
            "inputs": {"image": image_b64}
        },
        "3": {
            "class_type": "IPAdapterUnifiedLoader",
            "inputs": {
                "model": ["1", 0],
                "preset": "PLUS (high strength)"
            }
        },
        "4": {
            "class_type": "IPAdapter",
            "inputs": {
                "model": ["3", 0],
                "ipadapter": ["3", 1],
                "image": ["2", 0],
                "weight": strength,
                "weight_type": "style transfer",
                "start_at": 0.0,
                "end_at": 1.0
            }
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": prompt
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": "realistic, photo, 3d render, blurry, low quality"
            }
        },
        "7": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["2", 0],
                "vae": ["1", 2]
            }
        },
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["4", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["7", 0],
                "seed": 12345,
                "steps": 30,
                "cfg": 7.0,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": denoise
            }
        },
        "9": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["8", 0],
                "vae": ["1", 2]
            }
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["9", 0],
                "filename_prefix": f"test_{test_name}"
            }
        }
    }
    
    result = queue_prompt(workflow)
    if "prompt_id" in result:
        print(f"   Queued: {result['prompt_id']}")
        completion = wait_for_completion(result["prompt_id"])
        if completion:
            print(f"   Completed!")
            return True
    return False

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 이미지 로드
    if not os.path.exists(TEST_IMAGE):
        print(f"테스트 이미지가 없습니다: {TEST_IMAGE}")
        print("먼저 Family Guy 이미지를 저장해주세요.")
        exit(1)
    
    image_b64 = load_image_b64(TEST_IMAGE)
    
    # 프롬프트 정의
    edit_prompt = "Change this character to an Asian woman with black hair, keeping the exact same Family Guy cartoon art style, same pose, same clothing style"
    style_prompt = "Asian woman character in Family Guy cartoon style, black hair, standing pose, simple background, thick outlines, animated cartoon"
    
    print("=" * 60)
    print("Family Guy Character Edit Test Suite")
    print("=" * 60)
    
    # Test 1: Qwen Edit - 다양한 denoise 값
    for denoise in [0.5, 0.65, 0.75]:
        test_qwen_edit(image_b64, edit_prompt, denoise=denoise, test_name=f"qwen_d{int(denoise*100)}")
    
    # Test 2: USO Style Reference
    test_uso_style(image_b64, style_prompt, test_name="uso_style")
    
    # Test 3: IPAdapter - 다양한 설정
    for denoise, strength in [(0.5, 0.9), (0.6, 0.8), (0.7, 0.7)]:
        test_ipadapter(image_b64, style_prompt, denoise=denoise, strength=strength, 
                       test_name=f"ipa_d{int(denoise*100)}_s{int(strength*100)}")
    
    print("\n" + "=" * 60)
    print("테스트 완료! 결과 확인:")
    print(f"  ls -la {OUTPUT_DIR}/")
    print("=" * 60)
