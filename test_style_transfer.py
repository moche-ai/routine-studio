#!/usr/bin/env python3
"""Style Transfer Test Script - Based on Research Findings"""

import asyncio
import sys
import os
import json
import random
import base64
from datetime import datetime

sys.path.append("/data/routine/routine-studio-v2")
sys.path.append("/data/routine/routine-studio-v2/apps/api")

from services.comfyui import comfyui_service

# Test configurations based on research
TEST_CONFIGS = [
    {
        "name": "style_transfer_precise",
        "weight_type": "style transfer precise",
        "ipadapter_weight": 0.75,
        "description": "Precise style transfer - less bleeding between layers"
    }
]

async def build_workflow(
    positive_prompt: str,
    reference_image_b64: str,
    negative_prompt: str,
    config: dict,
    seed: int = -1
) -> dict:
    """Build IPAdapter style transfer workflow"""

    if seed == -1:
        seed = random.randint(0, 2**32 - 1)

    # Use existing workflow structure with ETN_LoadImageBase64
    workflow_template = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "animagineXL_v31.safetensors"
            }
        },
        "2": {
            "class_type": "CLIPVisionLoader",
            "inputs": {
                "clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
            }
        },
        "3": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {
                "ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"
            }
        },
        "4": {
            "class_type": "ETN_LoadImageBase64",
            "inputs": {
                "image": reference_image_b64
            }
        },
        "5": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["1", 0],
                "ipadapter": ["3", 0],
                "clip_vision": ["2", 0],
                "image": ["4", 0],
                "weight": config["ipadapter_weight"],
                "weight_type": config["weight_type"],
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 0.9,
                "embeds_scaling": "V only"
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": positive_prompt,
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
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            }
        },
        "9": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 30,
                "cfg": 7.5,
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
                "filename_prefix": "test_" + config["name"],
                "images": ["10", 0]
            }
        }
    }

    return workflow_template


async def run_test():
    """Run style transfer tests"""

    output_dir = "/data/routine/routine-studio-v2/output"
    os.makedirs(output_dir, exist_ok=True)

    # Load reference images
    ref_images = []
    for i in [1, 2]:
        with open(f"/data/routine/routine-studio-v2/test_images/ref_image{i}.b64", "r") as f:
            ref_images.append(f.read().strip())

    # Test prompt: Asian person in blue suit in cartoon style
    positive_prompt = "solo, 1person, single character, asian man, east asian, wearing blue suit, blue business suit, blue jacket, necktie, cartoon style, family guy style, simple background, clean lines, high quality, masterpiece"
    negative_prompt = "multiple people, 2girls, 2boys, two people, crowd, group, duo, couple, lowres, bad anatomy, bad hands, text, error, cropped, worst quality, low quality, blurry, deformed, realistic, photo, photograph"

    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for ref_idx, ref_image in enumerate(ref_images, 1):
        print("\n" + "=" * 60)
        print(f"Testing with Reference Image {ref_idx}")
        print("=" * 60)

        for config in TEST_CONFIGS:
            cfg_name = config["name"]
            cfg_desc = config["description"]
            cfg_weight_type = config["weight_type"]
            cfg_weight = config["ipadapter_weight"]

            print(f"\nConfig: {cfg_name}")
            print(f"Description: {cfg_desc}")
            print(f"Weight Type: {cfg_weight_type}")
            print(f"Weight: {cfg_weight}")

            for img_num in range(1, 6):  # Generate 5 images
                print(f"  Generating image {img_num}/5...")

                try:
                    workflow = await build_workflow(
                        positive_prompt=positive_prompt,
                        reference_image_b64=ref_image,
                        negative_prompt=negative_prompt,
                        config=config
                    )

                    images = await comfyui_service.execute_workflow(workflow, timeout=180)

                    if images:
                        filename = f"{output_dir}/ref{ref_idx}_{cfg_name}_{img_num}_{timestamp}.png"

                        img_data = images[0]
                        if img_data.startswith("data:"):
                            img_data = img_data.split(",", 1)[1]

                        with open(filename, "wb") as f:
                            f.write(base64.b64decode(img_data))

                        print(f"    Saved: {filename}")
                        results.append({
                            "ref_image": ref_idx,
                            "config": cfg_name,
                            "image_num": img_num,
                            "filename": filename,
                            "success": True
                        })
                    else:
                        print(f"    No image returned")
                        results.append({
                            "ref_image": ref_idx,
                            "config": cfg_name,
                            "image_num": img_num,
                            "success": False,
                            "error": "No image returned"
                        })

                except Exception as e:
                    print(f"    Error: {e}")
                    results.append({
                        "ref_image": ref_idx,
                        "config": cfg_name,
                        "image_num": img_num,
                        "success": False,
                        "error": str(e)
                    })

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"Total: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if successful:
        print(f"\nGenerated images saved to: {output_dir}")
        for r in successful:
            print(f"  - {r['filename']}")

    return results


if __name__ == "__main__":
    results = asyncio.run(run_test())
