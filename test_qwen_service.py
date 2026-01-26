#!/usr/bin/env python3
"""Test Qwen Image Edit using workflow_service"""

import asyncio
import sys
import os
import base64
from datetime import datetime

sys.path.append("/data/routine/routine-studio-v2")
sys.path.append("/data/routine/routine-studio-v2/apps/api")

from services.comfyui import comfyui_service
from services.workflow import workflow_service


async def test_qwen_edit():
    output_dir = "/data/routine/routine-studio-v2/output"
    os.makedirs(output_dir, exist_ok=True)

    # Load reference image 2 (blue suit character)
    with open("/data/routine/routine-studio-v2/test_images/ref_image2.b64", "r") as f:
        ref_b64 = f.read().strip()

    edit_instructions = [
        "make this character asian, keep cartoon style same",
        "change character to asian man, maintain the cartoon art style",
        "transform to east asian man, same style"
    ]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 60)
    print("Testing Qwen Image Edit via workflow_service")
    print("=" * 60)

    for idx, instruction in enumerate(edit_instructions, 1):
        print(f"\n[{idx}] {instruction}")

        for denoise in [0.5, 0.65]:
            print(f"  Denoise: {denoise}")

            try:
                workflow = workflow_service.build_qwen_image_edit(
                    input_image_b64=ref_b64,
                    edit_instruction=instruction,
                    denoise=denoise
                )

                images = await comfyui_service.execute_workflow(workflow, timeout=180)

                if images:
                    filename = f"{output_dir}/qwen_svc_{idx}_d{int(denoise*100)}_{timestamp}.png"

                    img_data = images[0]
                    if img_data.startswith("data:"):
                        img_data = img_data.split(",", 1)[1]

                    with open(filename, "wb") as f:
                        f.write(base64.b64decode(img_data))

                    print(f"    Saved: {filename}")
                else:
                    print(f"    No image returned")

            except Exception as e:
                print(f"    Error: {e}")

    print("\n" + "=" * 60)
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(test_qwen_edit())
