"""ComfyUI 워크플로우 템플릿 - 개선된 버전"""

from typing import Dict, Any
import random


def get_first_image_workflow(
    prompt: str,
    negative_prompt: str = "blurry, low quality, text, watermark, signature, deformed, ugly, bad anatomy",
    checkpoint: str = "CartoonXL.safetensors",
    width: int = 1024,
    height: int = 1024,
    steps: int = 25,
    cfg: float = 7.0,
    seed: int = -1
) -> Dict[str, Any]:
    """첫 번째 캐릭터 이미지 생성 워크플로우 (레퍼런스용)"""
    
    if seed == -1:
        seed = random.randint(0, 2**32 - 1)
    
    return {
        "3": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": checkpoint
            }
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["3", 1]
            }
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_prompt,
                "clip": ["3", 1]
            }
        },
        "6": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            }
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["3", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0]
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["3", 2]
            }
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "routine_first",
                "images": ["8", 0]
            }
        }
    }


def get_consistent_image_workflow(
    prompt: str,
    reference_image_path: str,
    negative_prompt: str = "blurry, low quality, text, watermark, signature, deformed, ugly, bad anatomy",
    checkpoint: str = "CartoonXL.safetensors",
    ip_adapter_weight: float = 0.7,
    width: int = 1024,
    height: int = 1024,
    steps: int = 25,
    cfg: float = 7.0,
    seed: int = -1
) -> Dict[str, Any]:
    """IP-Adapter로 일관된 캐릭터 이미지 생성"""
    
    if seed == -1:
        seed = random.randint(0, 2**32 - 1)
    
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": checkpoint
            }
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {
                "image": reference_image_path
            }
        },
        "3": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {
                "ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"
            }
        },
        "4": {
            "class_type": "CLIPVisionLoader",
            "inputs": {
                "clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
            }
        },
        "5": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "weight": ip_adapter_weight,
                "weight_type": "linear",
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 1.0,
                "embeds_scaling": "V only",
                "model": ["1", 0],
                "ipadapter": ["3", 0],
                "image": ["2", 0],
                "clip_vision": ["4", 0]
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["1", 1]
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_prompt,
                "clip": ["1", 1]
            }
        },
        "8": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            }
        },
        "9": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["5", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["8", 0]
            }
        },
        "10": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["9", 0],
                "vae": ["1", 2]
            }
        },
        "11": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "routine_scene",
                "images": ["10", 0]
            }
        }
    }


def get_wan_i2v_workflow(
    image_path: str,
    prompt: str,
    negative_prompt: str = "blurry, low quality, static, no motion, deformed, distorted, disfigured, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, disconnected limbs, mutation, mutated, ugly, disgusting, amputation",
    width: int = 832,
    height: int = 480,
    num_frames: int = 81,
    steps: int = 30,
    cfg: float = 6.0,
    seed: int = -1,
    noise_aug: float = 0.0,
    start_strength: float = 1.0,
    end_strength: float = 1.0
) -> Dict[str, Any]:
    """Wan2.2 Image to Video 워크플로우 - 개선된 버전
    
    Args:
        image_path: ComfyUI input 폴더 기준 이미지 경로
        prompt: 영상 프롬프트 (영어)
        negative_prompt: 네거티브 프롬프트
        width: 출력 너비 (16의 배수)
        height: 출력 높이 (16의 배수)
        num_frames: 프레임 수 (41 = ~1.7초, 81 = ~3.4초 @ 24fps)
        steps: 샘플링 스텝 수 (높을수록 품질 향상, 30-50 권장)
        cfg: CFG 스케일 (4-8 권장)
        seed: 랜덤 시드
        noise_aug: 노이즈 강도 (0.0-0.3, 모션 추가)
        start_strength: 시작 프레임 강도
        end_strength: 끝 프레임 강도
    """
    
    if seed == -1:
        seed = random.randint(0, 2**63 - 1)
    
    return {
        # 1. WanVideo 모델 로더
        "1": {
            "class_type": "WanVideoModelLoader",
            "inputs": {
                "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
                "base_precision": "bf16",
                "quantization": "disabled",
                "load_device": "offload_device"
            }
        },
        # 2. VAE 로더
        "2": {
            "class_type": "WanVideoVAELoader",
            "inputs": {
                "model_name": "wan_2.2_vae.safetensors",
                "precision": "bf16"
            }
        },
        # 3. UMT5 텍스트 인코더 로더
        "3": {
            "class_type": "LoadWanVideoT5TextEncoder",
            "inputs": {
                "model_name": "umt5-xxl-enc-bf16.safetensors",
                "precision": "bf16",
                "load_device": "offload_device"
            }
        },
        # 4. CLIP Vision 로더
        "4": {
            "class_type": "CLIPVisionLoader",
            "inputs": {
                "clip_name": "clip_vision_h.safetensors"
            }
        },
        # 5. 이미지 로드
        "5": {
            "class_type": "LoadImage",
            "inputs": {
                "image": image_path
            }
        },
        # 6. 이미지 리사이즈 (비율 유지, 16 배수)
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
        # 7. 텍스트 인코딩
        "7": {
            "class_type": "WanVideoTextEncode",
            "inputs": {
                "positive_prompt": prompt,
                "negative_prompt": negative_prompt,
                "t5": ["3", 0],
                "force_offload": True
            }
        },
        # 8. CLIP Vision 인코딩
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
        # 9. I2V 인코딩 (조정된 파라미터)
        "9": {
            "class_type": "WanVideoImageToVideoEncode",
            "inputs": {
                "width": width,
                "height": height,
                "num_frames": num_frames,
                "noise_aug_strength": noise_aug,
                "start_latent_strength": start_strength,
                "end_latent_strength": end_strength,
                "force_offload": True,
                "vae": ["2", 0],
                "clip_embeds": ["8", 0],
                "start_image": ["6", 0]
            }
        },
        # 10. 샘플링
        "10": {
            "class_type": "WanVideoSampler",
            "inputs": {
                "model": ["1", 0],
                "image_embeds": ["9", 0],
                "steps": steps,
                "cfg": cfg,
                "shift": 5.0,
                "seed": seed,
                "force_offload": True,
                "scheduler": "unipc",
                "riflex_freq_index": 0,
                "text_embeds": ["7", 0]
            }
        },
        # 11. 디코딩 (더 작은 타일로 품질 향상)
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
        # 12. 비디오 저장
        "12": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["11", 0],
                "frame_rate": 24,
                "loop_count": 0,
                "filename_prefix": "routine_video",
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
