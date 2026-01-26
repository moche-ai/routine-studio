#!/usr/bin/env python3
"""Image Quality Validator using Vision-Language Model"""

import asyncio
import sys
import json
import base64
from typing import Dict, Any, Optional, List, Tuple

sys.path.append("/data/routine/routine-studio-v2")
sys.path.append("/data/routine/routine-studio-v2/apps/api")

from services.vision import vision_service


class ImageValidator:
    """VL 모델을 사용한 이미지 품질 검증기"""

    VALIDATION_PROMPT = """Analyze this AI-generated cartoon character image and answer these questions in JSON format:

1. character_count: How many distinct characters/people are in the image? (number)
2. is_cartoon_style: Is it in cartoon/animated style (not realistic)? (true/false)
3. has_clear_face: Does the character have clear, well-defined facial features? (true/false)
4. clothing_color: What is the main color of the character's suit/clothing? (string)
5. clothing_type: What type of clothing is the character wearing? (string)
6. quality_issues: List any quality issues like deformed features, extra limbs, etc. (array)
7. overall_quality: Rate the overall quality from 1-10 (number)
8. style_consistency: Does it maintain a consistent cartoon style throughout? (true/false)

Return ONLY valid JSON, no other text:
{"character_count": 1, "is_cartoon_style": true, "has_clear_face": true, "clothing_color": "blue", "clothing_type": "suit", "quality_issues": [], "overall_quality": 8, "style_consistency": true}
"""

    def __init__(self):
        self.min_quality_score = 7
        self.required_character_count = 1

    async def validate_image(
        self,
        image_data: str,
        expected_clothing_color: str = "blue",
        expected_clothing_type: str = "suit"
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        이미지 검증

        Returns:
            (passed: bool, analysis: dict, reason: str)
        """
        try:
            # VL 모델로 이미지 분석
            analysis_result = await vision_service.analyze_image(
                image_data,
                self.VALIDATION_PROMPT
            )

            # JSON 파싱
            try:
                if "{" in analysis_result:
                    json_str = analysis_result[analysis_result.find("{"):analysis_result.rfind("}")+1]
                    analysis = json.loads(json_str)
                else:
                    return False, {}, "Failed to parse VL response as JSON"
            except json.JSONDecodeError as e:
                return False, {}, f"JSON parse error: {e}"

            # 검증 규칙 적용
            failures = []

            # 1. 캐릭터 수 체크
            char_count = analysis.get("character_count", 0)
            if char_count != self.required_character_count:
                failures.append(f"Character count: {char_count} (expected: {self.required_character_count})")

            # 2. 카툰 스타일 체크
            if not analysis.get("is_cartoon_style", False):
                failures.append("Not in cartoon style")

            # 3. 얼굴 품질 체크
            if not analysis.get("has_clear_face", False):
                failures.append("Face is not clearly defined")

            # 4. 의상 색상 체크
            clothing_color = analysis.get("clothing_color", "").lower()
            if expected_clothing_color.lower() not in clothing_color:
                failures.append(f"Clothing color: {clothing_color} (expected: {expected_clothing_color})")

            # 5. 의상 타입 체크
            clothing_type = analysis.get("clothing_type", "").lower()
            if expected_clothing_type.lower() not in clothing_type:
                failures.append(f"Clothing type: {clothing_type} (expected: {expected_clothing_type})")

            # 6. 전체 품질 점수 체크
            quality_score = analysis.get("overall_quality", 0)
            if quality_score < self.min_quality_score:
                failures.append(f"Quality score: {quality_score} (minimum: {self.min_quality_score})")

            # 7. 스타일 일관성 체크
            if not analysis.get("style_consistency", False):
                failures.append("Style is not consistent")

            # 8. 품질 이슈 체크
            quality_issues = analysis.get("quality_issues", [])
            if quality_issues:
                failures.append(f"Quality issues: {', '.join(quality_issues)}")

            # 결과 반환
            passed = len(failures) == 0
            reason = "PASSED" if passed else "; ".join(failures)

            return passed, analysis, reason

        except Exception as e:
            return False, {}, f"Validation error: {str(e)}"

    async def validate_and_filter(
        self,
        images: List[str],
        expected_clothing_color: str = "blue",
        expected_clothing_type: str = "suit"
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        여러 이미지 검증 후 통과한 것만 반환

        Returns:
            List of (image_data, analysis) for passed images
        """
        passed_images = []

        for i, image_data in enumerate(images):
            print(f"  Validating image {i+1}/{len(images)}...")
            passed, analysis, reason = await self.validate_image(
                image_data,
                expected_clothing_color,
                expected_clothing_type
            )

            if passed:
                print(f"    PASSED (quality: {analysis.get('overall_quality', '?')}/10)")
                passed_images.append((image_data, analysis))
            else:
                print(f"    FAILED: {reason}")

        return passed_images


# 테스트 코드
async def test_validator():
    """테스트"""
    validator = ImageValidator()

    # 이전에 생성한 이미지들로 테스트
    import os
    output_dir = "/data/routine/routine-studio-v2/output"

    # 최근 생성된 이미지 찾기
    files = sorted([f for f in os.listdir(output_dir) if f.endswith(".png")])[-5:]

    print(f"Testing {len(files)} images...")

    for filename in files:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        print(f"\n{filename}:")
        passed, analysis, reason = await validator.validate_image(image_data)
        print(f"  Result: {'PASSED' if passed else 'FAILED'}")
        print(f"  Reason: {reason}")
        if analysis:
            print(f"  Quality: {analysis.get('overall_quality', '?')}/10")
            print(f"  Clothing: {analysis.get('clothing_color', '?')} {analysis.get('clothing_type', '?')}")


if __name__ == "__main__":
    asyncio.run(test_validator())
