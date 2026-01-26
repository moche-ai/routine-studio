#!/usr/bin/env python3
"""Image Quality Validator v2 - Stricter validation"""

import asyncio
import sys
import json
import base64
import os
from typing import Dict, Any, Tuple, List

sys.path.append("/data/routine/routine-studio-v2")
sys.path.append("/data/routine/routine-studio-v2/apps/api")

from services.vision import vision_service


class ImageValidatorV2:
    """VL 모델을 사용한 엄격한 이미지 품질 검증기"""

    STRICT_VALIDATION_PROMPT = """You are a strict quality control AI for cartoon character images.
Analyze this image VERY CAREFULLY and be CRITICAL. Answer in JSON:

1. exact_character_count: Count EXACTLY how many human characters/people are visible (number, be precise)
2. cartoon_style_score: How well does it match Family Guy/American Dad cartoon style? (1-10, be strict)
3. face_quality_score: How clear and well-drawn are the facial features? No deformities? (1-10, be very strict)
4. suit_color: What is the EXACT color of the suit/jacket? (string: "blue", "white", "gray", "mixed", etc.)
5. suit_accuracy: Is the character wearing a proper business suit with jacket and pants? (1-10)
6. asian_features: Does the character have distinctly East Asian features? (true/false)
7. line_quality: Are the outlines clean and consistent? (1-10)
8. deformities: List ANY anatomical issues (extra fingers, weird proportions, etc.) (array)
9. overall_professional_quality: Would this be acceptable for a professional YouTube channel? (1-10, be harsh)

BE STRICT! Most AI images have subtle issues. Only give 8+ if it's genuinely excellent.

Return ONLY JSON:
{"exact_character_count": 1, "cartoon_style_score": 7, "face_quality_score": 6, "suit_color": "blue", "suit_accuracy": 8, "asian_features": true, "line_quality": 7, "deformities": ["slightly odd hand"], "overall_professional_quality": 6}
"""

    def __init__(self):
        self.min_quality_score = 7
        self.min_face_quality = 7
        self.min_line_quality = 6
        self.min_suit_accuracy = 7

    async def validate_image(
        self,
        image_data: str,
        expected_suit_color: str = "blue"
    ) -> Tuple[bool, Dict[str, Any], str]:
        """엄격한 이미지 검증"""
        try:
            result = await vision_service.analyze_image(image_data, self.STRICT_VALIDATION_PROMPT)

            # JSON 파싱
            try:
                if "{" in result:
                    json_str = result[result.find("{"):result.rfind("}")+1]
                    analysis = json.loads(json_str)
                else:
                    return False, {}, "Failed to parse JSON"
            except json.JSONDecodeError as e:
                return False, {}, f"JSON error: {e}"

            failures = []

            # 1. 캐릭터 수 (정확히 1명)
            char_count = analysis.get("exact_character_count", 0)
            if char_count != 1:
                failures.append(f"Characters: {char_count} (need exactly 1)")

            # 2. 카툰 스타일 점수
            style_score = analysis.get("cartoon_style_score", 0)
            if style_score < 6:
                failures.append(f"Style: {style_score}/10 (min: 6)")

            # 3. 얼굴 품질 (엄격)
            face_quality = analysis.get("face_quality_score", 0)
            if face_quality < self.min_face_quality:
                failures.append(f"Face quality: {face_quality}/10 (min: {self.min_face_quality})")

            # 4. 양복 색상 체크
            suit_color = analysis.get("suit_color", "").lower()
            if expected_suit_color.lower() not in suit_color and suit_color != expected_suit_color.lower():
                failures.append(f"Suit color: '{suit_color}' (expected: '{expected_suit_color}')")

            # 5. 양복 정확도
            suit_accuracy = analysis.get("suit_accuracy", 0)
            if suit_accuracy < self.min_suit_accuracy:
                failures.append(f"Suit accuracy: {suit_accuracy}/10 (min: {self.min_suit_accuracy})")

            # 6. 라인 품질
            line_quality = analysis.get("line_quality", 0)
            if line_quality < self.min_line_quality:
                failures.append(f"Line quality: {line_quality}/10 (min: {self.min_line_quality})")

            # 7. 기형 체크
            deformities = analysis.get("deformities", [])
            if deformities and len(deformities) > 0:
                failures.append(f"Deformities: {', '.join(str(d) for d in deformities)}")

            # 8. 전문적 품질
            pro_quality = analysis.get("overall_professional_quality", 0)
            if pro_quality < self.min_quality_score:
                failures.append(f"Professional quality: {pro_quality}/10 (min: {self.min_quality_score})")

            passed = len(failures) == 0
            reason = "PASSED" if passed else "; ".join(failures)

            return passed, analysis, reason

        except Exception as e:
            return False, {}, f"Error: {str(e)}"


async def test_all_images():
    """모든 생성 이미지 테스트"""
    validator = ImageValidatorV2()
    output_dir = "/data/routine/routine-studio-v2/output"

    # 모든 테스트 이미지
    files = sorted([f for f in os.listdir(output_dir) if f.startswith("ref") and f.endswith(".png")])

    print(f"Testing {len(files)} images with STRICT validation...\n")

    passed_count = 0
    results = []

    for filename in files:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        passed, analysis, reason = await validator.validate_image(image_data)

        status = "PASS" if passed else "FAIL"
        pro_quality = analysis.get("overall_professional_quality", "?")
        suit_color = analysis.get("suit_color", "?")

        print(f"{status} | Q:{pro_quality}/10 | Suit:{suit_color:6} | {filename}")
        if not passed:
            print(f"     -> {reason}")

        if passed:
            passed_count += 1

        results.append({
            "filename": filename,
            "passed": passed,
            "quality": pro_quality,
            "suit_color": suit_color,
            "reason": reason
        })

    print(f"\n{'='*60}")
    print(f"TOTAL: {passed_count}/{len(files)} passed ({100*passed_count/len(files):.0f}%)")

    # 통과한 이미지 목록
    passed_files = [r["filename"] for r in results if r["passed"]]
    if passed_files:
        print(f"\nPASSED images:")
        for f in passed_files:
            print(f"  - {f}")

    return results


if __name__ == "__main__":
    asyncio.run(test_all_images())
