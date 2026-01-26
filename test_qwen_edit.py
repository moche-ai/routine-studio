#!/usr/bin/env python3
"""Test Qwen Image Edit for style-consistent character editing"""

import asyncio
import sys
import os
import random
import base64
from datetime import datetime

sys.path.append("/data/routine/routine-studio-v2")
sys.path.append("/data/routine/routine-studio-v2/apps/api")

from services.comfyui import comfyui_service


async def build_qwen_edit_workflow(
    input_image_b64: str,
    edit_instruction: str,
    denoise: float = 0.7,
    seed: int = -1
) -> dict:
    """Build Qwen Image Edit workflow"""

    if seed == -1:
        seed = random.randint(0, 2**32 - 1)

    return {
        "1": {
            "class_type": "ETN_LoadImageBase64",
            "inputs": {"image": input_image_b64}
        },
        "2": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "qwen_image_vae.safetensors"}
        },
        "3": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "qwen_image_edit_2511_fp8mixed.safetensors",
                "weight_dtype": "default"
            }
        },
        "4": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "clip_name2": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                "type": "hunyuan_image"
            }
        },
        "5": {
            "class_type": "TextEncodeQwenImageEditPlus",
            "inputs": {
                "prompt": edit_instruction,
                "clip": ["4", 0],
                "vae": ["2", 0],
                "image1": ["1", 0]
            }
        },
        "6": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["1", 0],
                "vae": ["2", 0]
            }
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["5", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": seed,
                "steps": 30,
                "cfg": 5.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": denoise
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["2", 0]
            }
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["8", 0],
                "filename_prefix": "qwen_edit_test"
            }
        }
    }


async def test_qwen_edit():
    output_dir = "/data/routine/routine-studio-v2/output"
    os.makedirs(output_dir, exist_ok=True)

    # Load reference images
    ref_images = {}
    for i in [1, 2]:
        with open(f"/data/routine/routine-studio-v2/test_images/ref_image{i}.b64", "r") as f:
            ref_images[i] = f.read().strip()

    # Edit instructions to test
    edit_instructions = [
        "Change the character to wear a dark navy blue business suit with blue jacket and blue pants, keep the cartoon style",
        "Transform this character into an Asian man wearing a blue suit, maintain the same cartoon art style",
        "Edit the clothing to be a navy blue formal suit, keep face and cartoon style same"
    ]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 60)
    print("Testing Qwen Image Edit")
    print("=" * 60)

    for ref_idx in [1, 2]:  # Test both references
        print(f"\n[Reference Image {ref_idx}]")
        ref_b64 = ref_images[ref_idx]

        for inst_idx, instruction in enumerate(edit_instructions, 1):
            print(f"\n  Instruction {inst_idx}: {instruction[:50]}...")

            # Test with different denoise values
            for denoise in [0.5, 0.7]:
                print(f"    Denoise: {denoise}")

                try:
                    workflow = await build_qwen_edit_workflow(
                        ref_b64, instruction, denoise=denoise
                    )

                    images = await comfyui_service.execute_workflow(workflow, timeout=180)

                    if images:
                        filename = f"{output_dir}/qwen_ref{ref_idx}_inst{inst_idx}_d{int(denoise*10)}_{timestamp}.png"

                        img_data = images[0]
                        if img_data.startswith("data:"):
                            img_data = img_data.split(",", 1)[1]

                        with open(filename, "wb") as f:
                            f.write(base64.b64decode(img_data))

                        print(f"      Saved: {filename}")
                    else:
                        print(f"      No image returned")

                except Exception as e:
                    print(f"      Error: {e}")

    print("\n" + "=" * 60)
    print("Test complete! Check output directory.")


if __name__ == "__main__":
    asyncio.run(test_qwen_edit())
