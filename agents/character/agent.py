import json
import sys
sys.path.append("/app")

from typing import Dict, Any, List, Optional
from agents.base import BaseAgent, AgentResult, AgentStatus
from apps.api.services.comfyui import comfyui_service
from apps.api.services.vision import vision_service
from apps.api.services.workflow import workflow_service

def emit_progress(status: str, detail: str = ""):
    try:
        import builtins
        if hasattr(builtins, "emit_agent_progress"):
            builtins.emit_agent_progress(status, detail)
    except:
        pass


class CharacterAgent(BaseAgent):
    """캐릭터 편집 에이전트 - VL 기반 의도 파악"""

    PHASE_CONCEPT = "concept"
    PHASE_GENERATION = "generation"

    # 의도 타입
    INTENT_USE_AS_IS = "use_as_is"      # 그대로 사용
    INTENT_EDIT = "edit"                # 편집 요청
    INTENT_CONFIRM = "confirm"          # 확정
    INTENT_UNKNOWN = "unknown"          # 불명확

    def __init__(self):
        super().__init__("CharacterAgent")
        self.reference_image: Optional[str] = None
        self.phase = self.PHASE_CONCEPT

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        self.status = AgentStatus.RUNNING
        self.phase = self.PHASE_CONCEPT

        channel_name = input_data.get("selected_channel_name", "")
        self.set_context("channel_name", channel_name)

        message = """**캐릭터 편집 에이전트**

**이미지를 첨부**하고 원하는 것을 말해주세요!

예시:
• "이 캐릭터 쓸게" - 그대로 사용
• "금발로 바꿔줘" - 편집
• "배경 제거해줘" - 배경 제거

주의: 성별 변경은 어려울 수 있습니다."""

        self.status = AgentStatus.WAITING_FEEDBACK
        return AgentResult(success=True, step="character", message=message, needs_feedback=True)

    async def _analyze_intent(self, feedback: str, has_image: bool) -> Dict[str, Any]:
        """VL 모델로 사용자 의도 분석"""

        prompt = f'''사용자 메시지를 분석하고 의도를 파악하세요.

메시지: "{feedback}"
이미지 첨부: {"있음" if has_image else "없음"}

다음 중 하나를 선택:
1. use_as_is: 이미지를 편집 없이 그대로 사용하겠다는 의도 (예: "이거 쓸게", "이 캐릭터로", "그대로", "이걸로 할게")
2. edit: 이미지를 편집/수정하겠다는 의도 (예: "금발로", "안경 추가", "옷 바꿔")
3. confirm: 결과를 확정하겠다는 의도 (예: "확정", "좋아", "완료")
4. unknown: 의도 불분명

JSON 형식으로만 응답:
{{"intent": "use_as_is|edit|confirm|unknown", "edit_request": "편집 요청 내용 (edit인 경우만)"}}'''

        try:
            from apps.api.services.llm import llm_service
            response = await llm_service.generate(prompt, max_tokens=200)

            # JSON 파싱
            text = response.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            result = json.loads(text)
            print(f"[CharacterAgent] Intent analysis: {result}")
            return result
        except Exception as e:
            print(f"[CharacterAgent] Intent analysis failed: {e}")
            # 폴백: 간단한 키워드 매칭
            return self._fallback_intent(feedback)

    def _fallback_intent(self, feedback: str) -> Dict[str, Any]:
        """LLM 실패시 폴백 키워드 매칭"""
        feedback_lower = feedback.lower()

        # 확정 키워드
        if any(kw in feedback for kw in ["확정", "좋아", "완료", "ok", "오케이"]):
            return {"intent": self.INTENT_CONFIRM}

        # 그대로 사용 키워드
        use_keywords = ["이거 쓸", "이거로", "이걸로", "그대로", "쓸게", "쓸래", "사용할", "사용해", "이 캐릭터", "이 이미지"]
        if any(kw in feedback for kw in use_keywords):
            return {"intent": self.INTENT_USE_AS_IS}

        # 편집 키워드가 있으면 edit
        edit_keywords = ["바꿔", "변경", "수정", "추가", "제거", "으로", "로 ", "해줘"]
        if any(kw in feedback for kw in edit_keywords):
            return {"intent": self.INTENT_EDIT, "edit_request": feedback}

        return {"intent": self.INTENT_UNKNOWN}

    async def handle_feedback(self, feedback: str, images: List[str] = None) -> AgentResult:
        has_image = images and len(images) > 0

        # 의도 분석
        intent_result = await self._analyze_intent(feedback, has_image)
        intent = intent_result.get("intent", self.INTENT_UNKNOWN)

        print(f"[CharacterAgent] Detected intent: {intent}, phase: {self.phase}")

        # 확정 의도
        if intent == self.INTENT_CONFIRM:
            if self.phase == self.PHASE_GENERATION:
                self.status = AgentStatus.COMPLETED
                return AgentResult(
                    success=True, step="character_confirmed",
                    message="캐릭터가 확정되었습니다!",
                    images=self.get_context("generated_images", [])
                )

        # 이미지가 있는 경우
        if has_image:
            self.reference_image = images[0]
            self.set_context("reference_image", images[0])

            # 그대로 사용
            if intent == self.INTENT_USE_AS_IS:
                return await self._use_existing_character(images[0])

            # 편집 요청
            if intent == self.INTENT_EDIT:
                edit_request = intent_result.get("edit_request", feedback)
                return await self._qwen_edit(edit_request, images[0])

            # 의도 불분명 - 물어보기
            return AgentResult(
                success=True, step="character",
                message="이미지를 받았어요!\n\n• 그대로 사용: '이거 쓸게'\n• 편집: 변경 사항 입력",
                images=images, needs_feedback=True
            )

        # 이미지 없이 피드백만 온 경우
        if feedback.strip():
            # 기존 이미지가 있으면 편집
            target = self.get_context("generated_images", [])
            if target:
                return await self._qwen_edit(feedback, target[0])
            elif self.reference_image:
                return await self._qwen_edit(feedback, self.reference_image)

        return AgentResult(
            success=True, step="character",
            message="이미지를 첨부하고 원하는 것을 말해주세요!",
            needs_feedback=True
        )

    async def _qwen_edit(self, user_request: str, image_data: str) -> AgentResult:
        """Qwen Edit + LoRA"""

        img = image_data
        if img and img.startswith("data:"):
            img = img.split(",", 1)[1]

        # 배경 제거
        if any(kw in user_request for kw in ["배경 제거", "배경 없", "투명 배경"]):
            return await self._remove_background(image_data)

        emit_progress("이미지 분석", "Qwen3-VL 분석 중...")

        # Vision 분석으로 edit instruction 생성
        try:
            analysis = await vision_service.analyze_character_for_edit(img, user_request)
            edit_instruction = analysis.get("edit_instruction", "")
            print(f"[CharacterAgent] Vision analysis: {json.dumps(analysis, ensure_ascii=False)}")
        except Exception as e:
            print(f"[CharacterAgent] Vision failed: {e}")
            edit_instruction = ""

        if not edit_instruction:
            edit_instruction = f"Edit this character: {user_request}. Keep the same art style."

        denoise = 0.75
        emit_progress("이미지 생성", f"Qwen Edit / denoise: {denoise}")

        try:
            workflow = workflow_service.build_qwen_edit_with_lora(
                input_image_b64=img,
                edit_instruction=edit_instruction,
                denoise=denoise,
                lora_strength=0.9,
                steps=30,
                cfg=5.0,
                output_prefix="char_edit"
            )

            images = await comfyui_service.execute_workflow(workflow, timeout=300)
            self.set_context("generated_images", images)
            self.phase = self.PHASE_GENERATION
            self.status = AgentStatus.WAITING_FEEDBACK

            return AgentResult(
                success=True, step="character",
                message=f"편집 완료!\n\n• denoise: {denoise}\n• instruction: {edit_instruction[:100]}...\n\n추가 수정이 필요하면 말씀해주세요. 완료는 '확정'",
                images=images, needs_feedback=True
            )

        except Exception as e:
            print(f"[CharacterAgent] Edit failed: {e}")
            import traceback
            traceback.print_exc()
            return AgentResult(
                success=True, step="character",
                message=f"편집 실패: {e}",
                needs_feedback=True
            )

    async def _use_existing_character(self, image_data: str) -> AgentResult:
        """기존 이미지를 캐릭터로 사용 (편집 없이)"""
        emit_progress("캐릭터 분석", "이미지 분석 중...")

        img = image_data
        if img and img.startswith("data:"):
            img = img.split(",", 1)[1]

        # 채널 정보 가져오기
        channel_name = self.get_context("channel_name", "")

        # VL로 캐릭터 상세 분석
        analysis = {}
        try:
            analysis = await vision_service.describe_character(img)
            print(f"[CharacterAgent] Character analysis: {analysis}")
        except Exception as e:
            print(f"[CharacterAgent] Vision analysis failed: {e}")

        # 이미지 저장
        self.set_context("generated_images", [image_data])
        self.set_context("character_analysis", analysis)
        self.phase = self.PHASE_GENERATION
        self.status = AgentStatus.COMPLETED

        # 기본 메시지 (orchestrator에서 스토리텔링으로 대체됨)
        message = "캐릭터가 등록되었습니다!"

        return AgentResult(
            success=True,
            step="character_confirmed",
            message=message,
            images=[image_data],
            data={"character_analysis": analysis, "channel_name": channel_name}
        )

    async def _remove_background(self, image_data: str) -> AgentResult:
        emit_progress("배경 제거", "RemBG 처리 중...")

        img = image_data
        if img and img.startswith("data:"):
            img = img.split(",", 1)[1]

        try:
            workflow = workflow_service.build_remove_background(input_image_b64=img)
            images = await comfyui_service.execute_workflow(workflow, timeout=120)
            self.set_context("generated_images", images)
            self.phase = self.PHASE_GENERATION
            self.status = AgentStatus.WAITING_FEEDBACK

            return AgentResult(
                success=True, step="character",
                message="배경 제거 완료!",
                images=images, needs_feedback=True
            )
        except Exception as e:
            return AgentResult(
                success=True, step="character",
                message=f"배경 제거 실패: {e}",
                needs_feedback=True
            )
