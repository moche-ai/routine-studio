import json
import sys
import re

sys.path.append("/app")

from typing import Dict, Any, List, Optional
from agents.base import BaseAgent, AgentResult, AgentStatus
from apps.api.services.llm import llm_service
from .prompts import PROMPTS


def extract_json(text: str) -> Optional[Dict]:
    if "{" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        json_str = text[start:end]
        try:
            return json.loads(json_str)
        except:
            json_str = json_str.replace("\n", "\\n")
            try:
                return json.loads(json_str)
            except:
                pass
    return None


def filter_korean_english_only(names: list) -> list:
    """한글과 영어만 포함된 이름만 필터링"""
    import re

    result = []
    # 한글, 영어, 숫자, 공백, 기본 특수문자만 허용
    pattern = re.compile(r"^[가-힣a-zA-Z0-9\s\-_&.!?]+$")
    for name in names:
        if pattern.match(name):
            result.append(name)
    return result if result else names[:5]  # 모두 필터링되면 원본 일부 반환


class PlannerAgent(BaseAgent):
    STEPS = ["channel_name", "character", "video_ideas", "script"]

    # 설문 옵션 정의
    STYLE_OPTIONS = {
        1: {
            "label": "전문적/신뢰감",
            "keywords": ["전문", "신뢰", "권위", "공식", "인사이트"],
        },
        2: {
            "label": "친근하고 재미있는",
            "keywords": ["재미", "유쾌", "친근", "웃음", "편한"],
        },
        3: {
            "label": "트렌디/젊은",
            "keywords": ["트렌디", "젊은", "MZ", "핫한", "신선"],
        },
        4: {
            "label": "감성적/따뜻한",
            "keywords": ["감성", "따뜻", "힐링", "공감", "위로"],
        },
    }

    LANGUAGE_OPTIONS = {
        1: {"label": "순한글", "style": "korean"},
        2: {"label": "영어", "style": "english"},
        3: {"label": "한글+영어 믹스", "style": "mixed"},
        4: {"label": "상관없음", "style": "any"},
    }

    def __init__(self):
        super().__init__("PlannerAgent")
        self.current_step = 0

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        step = input_data.get("step", self.STEPS[self.current_step])

        if step == "channel_name":
            return await self._start_channel_name_survey(input_data)
        elif step == "character":
            return await self._handle_character(input_data)
        elif step == "video_ideas":
            return await self._generate_video_ideas(input_data)
        elif step == "script":
            return await self._generate_script(input_data)

        return AgentResult(success=False, message=f"알 수 없는 단계: {step}")

    async def _start_channel_name_survey(self, input_data: Dict) -> AgentResult:
        """채널명 생성 - 1단계: 선호 채널명 먼저 물어보기"""
        self.status = AgentStatus.RUNNING

        user_request = input_data.get("user_request", "")
        self.set_context("user_request", user_request)
        self.set_context("survey_step", "ask_preferred")

        self.status = AgentStatus.WAITING_FEEDBACK

        return AgentResult(
            success=True,
            step="channel_name_survey",
            message=f"'{user_request}' 채널을 만드시려는군요!\n\n혹시 원하시는 채널명이 있으신가요?\n직접 입력하시거나, AI가 추천해드릴 수도 있어요.",
            data={
                "type": "quick_buttons",
                "survey_step": "ask_preferred",
                "buttons": [{"label": "추천해줘", "value": "추천해줘"}],
            },
            needs_feedback=True,
        )

    async def _handle_survey_response(self, feedback: str) -> AgentResult:
        """설문 응답 처리"""
        survey_step = self.get_context("survey_step", "style")
        num = self._extract_number(feedback)
        feedback_stripped = feedback.strip()

        # ========== ask_preferred 단계: 선호 채널명 물어보기 ==========
        if survey_step == "ask_preferred":
            # "추천해줘" 버튼 클릭 시 → 스타일 설문으로 진행
            if feedback_stripped == "추천해줘" or "추천" in feedback_stripped:
                self.set_context("survey_step", "style")

                options_text = "\n".join(
                    [f"**{k}.** {v['label']}" for k, v in self.STYLE_OPTIONS.items()]
                )

                return AgentResult(
                    success=True,
                    step="channel_name_survey",
                    message=f"어떤 느낌의 채널명을 원하시나요?\n\n{options_text}\n\n숫자를 선택하거나, 원하는 스타일을 직접 입력하세요 (예: 짧고 임팩트있게)",
                    data={
                        "type": "selection",
                        "survey_step": "style",
                        "options": [
                            {"id": k, "label": v["label"]}
                            for k, v in self.STYLE_OPTIONS.items()
                        ],
                    },
                    needs_feedback=True,
                )

            # 사용자가 텍스트 입력 시 → 확인 단계로
            if len(feedback_stripped) >= 1:
                self.set_context("preferred_channel_name", feedback_stripped)
                self.set_context("survey_step", "confirm_preferred")

                return AgentResult(
                    success=True,
                    step="channel_name_survey",
                    message=f"**'{feedback_stripped}'**\n\n이 채널명으로 확정할까요?",
                    data={
                        "type": "quick_buttons",
                        "survey_step": "confirm_preferred",
                        "buttons": [
                            {"label": "확정", "value": "확정"},
                            {"label": "다시 입력", "value": "다시 입력"},
                        ],
                    },
                    needs_feedback=True,
                )

        # ========== confirm_preferred 단계: 선호 채널명 확정 ==========
        if survey_step == "confirm_preferred":
            preferred_name = self.get_context("preferred_channel_name", "")

            if (
                "확정" in feedback_stripped
                or "좋아" in feedback_stripped
                or "이걸로" in feedback_stripped
            ):
                self.set_context("selected_channel_name", preferred_name)
                return AgentResult(
                    success=True,
                    step="channel_name_confirmed",
                    message=f"**{preferred_name}** 채널명이 확정되었습니다!",
                    data={"selected_channel_name": preferred_name},
                    needs_feedback=False,
                )

            if "다시" in feedback_stripped or "입력" in feedback_stripped:
                self.set_context("survey_step", "ask_preferred")
                return AgentResult(
                    success=True,
                    step="channel_name_survey",
                    message="원하시는 채널명을 입력해주세요.",
                    data={
                        "type": "quick_buttons",
                        "survey_step": "ask_preferred",
                        "buttons": [{"label": "추천해줘", "value": "추천해줘"}],
                    },
                    needs_feedback=True,
                )

            # 새로운 텍스트 입력 시 → 그걸로 다시 확인
            if len(feedback_stripped) >= 1:
                self.set_context("preferred_channel_name", feedback_stripped)
                return AgentResult(
                    success=True,
                    step="channel_name_survey",
                    message=f"**'{feedback_stripped}'**\n\n이 채널명으로 확정할까요?",
                    data={
                        "type": "quick_buttons",
                        "survey_step": "confirm_preferred",
                        "buttons": [
                            {"label": "확정", "value": "확정"},
                            {"label": "다시 입력", "value": "다시 입력"},
                        ],
                    },
                    needs_feedback=True,
                )

        # 텍스트 스타일 요청 감지 (2글자 이상, 순수 숫자가 아닌 경우)
        is_text_request = (
            len(feedback_stripped) >= 2
            and not feedback_stripped.isdigit()
            and num is None
        )

        if is_text_request and survey_step == "style":
            # 텍스트로 바로 채널명 생성 (설문 스킵)
            self.set_context("survey_step", "selection")
            return await self._regenerate_with_preference(feedback_stripped)

        if survey_step == "style":
            # 스타일 선택 처리
            if num and num in self.STYLE_OPTIONS:
                self.set_context("selected_style", num)
                self.set_context("survey_step", "language")

                # 언어 옵션 메시지
                options_text = "\n".join(
                    [f"**{k}.** {v['label']}" for k, v in self.LANGUAGE_OPTIONS.items()]
                )

                return AgentResult(
                    success=True,
                    step="channel_name_survey",
                    message=f"**{self.STYLE_OPTIONS[num]['label']}** 스타일이군요!\n\n채널명 언어 스타일은 어떤 게 좋을까요?\n\n{options_text}\n\n숫자를 입력해주세요:",
                    data={
                        "type": "selection",
                        "survey_step": "language",
                        "options": [
                            {"id": k, "label": v["label"]}
                            for k, v in self.LANGUAGE_OPTIONS.items()
                        ],
                    },
                    needs_feedback=True,
                )
            else:
                return AgentResult(
                    success=True,
                    step="channel_name_survey",
                    message="숫자(1~4)를 선택하거나, 원하는 스타일을 직접 입력하세요:",
                    needs_feedback=True,
                )

        elif survey_step == "language":
            # 언어 선택 후 채널명 생성
            if num and num in self.LANGUAGE_OPTIONS:
                self.set_context("selected_language", num)
                return await self._generate_channel_names_with_survey()
            else:
                return AgentResult(
                    success=True,
                    step="channel_name_survey",
                    message="숫자(1~4)를 선택하거나, 원하는 스타일을 직접 입력하세요:",
                    needs_feedback=True,
                )

        # 설문 완료 후 (채널명 선택 단계)
        return await self._handle_channel_name_selection(feedback)

    async def _generate_channel_names_with_survey(self) -> AgentResult:
        """설문 결과 기반 채널명 생성"""
        self.status = AgentStatus.RUNNING

        user_request = self.get_context("user_request", "")
        style_num = self.get_context("selected_style", 1)
        lang_num = self.get_context("selected_language", 4)

        style_info = self.STYLE_OPTIONS.get(style_num, self.STYLE_OPTIONS[1])
        lang_info = self.LANGUAGE_OPTIONS.get(lang_num, self.LANGUAGE_OPTIONS[4])

        # 언어 스타일 지시
        lang_instruction = {
            "korean": "순한글로만 작성 (영어 단어 사용 금지)",
            "english": "영어로만 작성 (한글 사용 금지)",
            "mixed": "한글과 영어를 적절히 섞어서 작성",
            "any": "한글과 영어만 사용 (일본어, 중국어 금지)",
        }.get(lang_info["style"], "")

        prompt = f"""유튜브 채널명 10개를 생성해주세요.

채널 주제: {user_request}
스타일: {style_info["label"]} (키워드: {", ".join(style_info["keywords"])})
언어: {lang_instruction}

[중요] 언어 제한:
- 반드시 한글(가-힣)과 영어(A-Z, a-z)만 사용하세요
- 일본어(ひらがな, カタカナ, 漢字), 중국어 절대 금지
- 위반 시 채널명 무효 처리됨

요구사항:
1. 기억하기 쉽고 독특한 이름
2. 검색에 잘 걸리는 이름
3. 채널 주제가 바로 느껴지는 이름
4. 스타일과 언어 조건을 꼭 지킬 것

JSON 형식으로만 응답:
{{"channel_names": ["이름1", "이름2", ..., "이름10"], "reasoning": "추천 이유"}}"""

        try:
            response = await llm_service.generate(prompt, temperature=0.9)
            data = extract_json(response)

            if not data or "channel_names" not in data:
                data = {
                    "channel_names": [f"채널{i}" for i in range(1, 11)],
                    "reasoning": "기본",
                }

            names_list = filter_korean_english_only(data["channel_names"][:10])
            self.set_context("channel_names", names_list)
            self.set_context("survey_step", "selection")
            self.status = AgentStatus.WAITING_FEEDBACK

            # 채널명 목록 포맷팅
            names_display = "\n".join(
                [f"**{i + 1}.** {name}" for i, name in enumerate(names_list)]
            )

            return AgentResult(
                success=True,
                step="channel_name",
                message=f'**{style_info["label"]}** 스타일 + **{lang_info["label"]}**로 채널명을 추천해드릴게요!\n\n{names_display}\n\n---\n원하는 번호를 선택하거나, 다른 요청을 해주세요:\n- "더 추천해줘" - 새로운 10개 생성\n- "좀 더 짧게" - 짧은 이름으로 재생성\n- "영어로" - 언어 변경',
                data={
                    "channel_names": names_list,
                    "type": "selection",
                    "options": [
                        {"id": i + 1, "label": name}
                        for i, name in enumerate(names_list)
                    ],
                },
                needs_feedback=True,
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(success=False, message=f"채널명 생성 실패: {str(e)}")

    async def _handle_channel_name_selection(self, feedback: str) -> AgentResult:
        """채널명 선택 또는 재요청 처리"""
        num = self._extract_number(feedback)
        names = self.get_context("channel_names", [])

        # 숫자 선택
        if num and 0 < num <= len(names):
            selected = names[num - 1]
            self.set_context("selected_channel_name", selected)
            return AgentResult(
                success=True,
                step="channel_name_confirmed",
                message=f"**{selected}** 채널명이 확정되었습니다!\n\n다음 단계로 진행하려면 확인을 입력해주세요.",
                data={"selected_channel_name": selected},
                needs_feedback=True,
            )

        # 재생성 요청 처리
        feedback_lower = feedback.lower()

        if (
            "더" in feedback
            or "다른" in feedback
            or "다시" in feedback
            or "재생성" in feedback
        ):
            # 새로운 채널명 생성
            return await self._generate_channel_names_with_survey()

        if "짧" in feedback:
            # 짧은 이름으로 재생성
            self.set_context("length_preference", "short")
            return await self._regenerate_with_preference("짧은 이름 (4글자 이하)")

        if "긴" in feedback or "길" in feedback:
            # 긴 이름으로 재생성
            self.set_context("length_preference", "long")
            return await self._regenerate_with_preference("긴 이름 (6글자 이상)")

        if "영어" in feedback or "english" in feedback_lower:
            self.set_context("selected_language", 2)
            return await self._generate_channel_names_with_survey()

        if "한글" in feedback or "한국어" in feedback:
            self.set_context("selected_language", 1)
            return await self._generate_channel_names_with_survey()

        if "전문" in feedback:
            self.set_context("selected_style", 1)
            return await self._generate_channel_names_with_survey()

        if "친근" in feedback or "재미" in feedback:
            self.set_context("selected_style", 2)
            return await self._generate_channel_names_with_survey()

        if "트렌디" in feedback or "mz" in feedback_lower:
            self.set_context("selected_style", 3)
            return await self._generate_channel_names_with_survey()

        if "감성" in feedback or "따뜻" in feedback:
            self.set_context("selected_style", 4)
            return await self._generate_channel_names_with_survey()

        # 확정 처리
        if any(kw in feedback for kw in ["확정", "좋아", "이걸로", "완료"]):
            if names:
                selected = names[0]
                self.set_context("selected_channel_name", selected)
                return AgentResult(
                    success=True,
                    step="channel_name_confirmed",
                    message=f"**{selected}** 채널명이 확정되었습니다!",
                    data={"selected_channel_name": selected},
                    needs_feedback=False,
                )

        # 자유로운 스타일 요청 처리 (3글자 이상의 텍스트)
        if len(feedback) >= 3:
            return await self._regenerate_with_preference(feedback)

        # 인식 못한 요청
        return AgentResult(
            success=True,
            step="channel_name",
            message='번호를 선택하거나, 스타일 요청을 해주세요:\n예: "위트있게", "짧고 임팩트있게", "영어로"',
            needs_feedback=True,
        )

    async def _regenerate_with_preference(self, preference: str) -> AgentResult:
        """특정 선호도로 채널명 재생성"""
        self.status = AgentStatus.RUNNING

        user_request = self.get_context("user_request", "")
        style_num = self.get_context("selected_style", 1)
        lang_num = self.get_context("selected_language", 4)

        style_info = self.STYLE_OPTIONS.get(style_num, self.STYLE_OPTIONS[1])
        lang_info = self.LANGUAGE_OPTIONS.get(lang_num, self.LANGUAGE_OPTIONS[4])

        lang_instruction = {
            "korean": "순한글로만 작성",
            "english": "영어로만 작성",
            "mixed": "한글과 영어를 믹스",
            "any": "언어 제한 없음",
        }.get(lang_info["style"], "")

        prompt = f"""유튜브 채널명 10개를 생성해주세요.

채널 주제: {user_request}
스타일: {style_info["label"]}
언어: {lang_instruction}
특별 요청: {preference}

JSON 형식:
{{"channel_names": ["이름1", ..., "이름10"], "reasoning": "추천 이유"}}"""

        try:
            response = await llm_service.generate(prompt, temperature=0.9)
            data = extract_json(response)

            if not data or "channel_names" not in data:
                data = {"channel_names": [f"채널{i}" for i in range(1, 11)]}

            names_list = filter_korean_english_only(data["channel_names"][:10])
            self.set_context("channel_names", names_list)
            self.status = AgentStatus.WAITING_FEEDBACK

            names_display = "\n".join(
                [f"**{i + 1}.** {name}" for i, name in enumerate(names_list)]
            )

            return AgentResult(
                success=True,
                step="channel_name",
                message=f"**{preference}**으로 다시 추천해드릴게요!\n\n{names_display}\n\n---\n원하는 번호를 선택하거나 추가 요청을 해주세요:",
                data={
                    "channel_names": names_list,
                    "type": "selection",
                    "options": [
                        {"id": i + 1, "label": name}
                        for i, name in enumerate(names_list)
                    ],
                },
                needs_feedback=True,
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(success=False, message=f"채널명 재생성 실패: {str(e)}")

    def _extract_number(self, text: str) -> Optional[int]:
        """텍스트에서 숫자 추출"""
        if text.strip().isdigit():
            return int(text.strip())

        match = re.search(r"(\d+)\s*번?", text)
        if match:
            return int(match.group(1))

        korean_nums = {
            "첫": 1,
            "두": 2,
            "세": 3,
            "네": 4,
            "다섯": 5,
            "여섯": 6,
            "일곱": 7,
            "여덟": 8,
            "아홉": 9,
            "열": 10,
        }
        for k, v in korean_nums.items():
            if k in text:
                return v

        return None

    async def _handle_character(self, input_data: Dict) -> AgentResult:
        """캐릭터 단계 - CharacterAgent로 위임"""
        return AgentResult(
            success=True,
            step="character",
            message="캐릭터 생성을 시작합니다.",
            data={"next_agent": "CharacterAgent"},
            needs_feedback=False,
        )

    async def handle_feedback(
        self, feedback: str, images: List[str] = None
    ) -> AgentResult:
        current_step = self.STEPS[self.current_step]

        # ========== CHANNEL_NAME 단계: 설문 및 선택 처리 ==========
        if current_step == "channel_name":
            survey_step = self.get_context("survey_step", "")

            # 설문 진행 중
            if survey_step in [
                "ask_preferred",
                "confirm_preferred",
                "style",
                "language",
            ]:
                return await self._handle_survey_response(feedback)

            # 채널명 선택 단계
            if survey_step == "selection":
                return await self._handle_channel_name_selection(feedback)

            # 기본: 새로 시작
            return await self._start_channel_name_survey(
                {"user_request": self.get_context("user_request", feedback)}
            )

        # ========== CHARACTER 단계에서 이미지 적용 ==========
        if current_step == "character" and images and len(images) > 0:
            if (
                "적용" in feedback
                or "이걸로" in feedback
                or "할께" in feedback
                or "할게" in feedback
            ):
                self.set_context("character_image", images[0])
                return AgentResult(
                    success=True,
                    step="character_confirmed",
                    message="캐릭터 이미지를 저장했습니다.\n\n이 캐릭터로 영상을 제작할게요. 이제 영상 아이디어를 생성할게요...",
                    data={
                        "character_image": images[0],
                        "auto_next": True,
                        "next_step": "video_ideas",
                    },
                    needs_feedback=False,
                )

        # ========== CHARACTER 확정 후 VIDEO_IDEAS로 이동 ==========
        if current_step == "character" and (
            "확정" in feedback or "다음" in feedback or "진행" in feedback
        ):
            self.current_step = 2  # video_ideas
            return await self.execute({"step": "video_ideas"})

        # ========== VIDEO_IDEAS 단계 피드백 처리 ==========
        if current_step == "video_ideas":
            numbers = re.findall(r"\d+", feedback)
            if numbers:
                selected_idx = int(numbers[0]) - 1
                ideas = self.get_context("video_ideas", [])
                if 0 <= selected_idx < len(ideas):
                    selected_idea = ideas[selected_idx]
                    self.set_context("selected_video_idea", selected_idea)
                    self.current_step = 3  # script
                    return await self.execute({"step": "script"})

            if "확정" in feedback or "좋아" in feedback:
                ideas = self.get_context("video_ideas", [])
                if ideas:
                    self.set_context("selected_video_idea", ideas[0])
                    self.current_step = 3  # script
                    return await self.execute({"step": "script"})

            if len(feedback) > 5 and not any(
                kw in feedback for kw in ["확정", "좋아", "이걸로", "선택"]
            ):
                return await self._generate_video_ideas(
                    {"step": "video_ideas", "user_topic": feedback, "regenerate": True}
                )

        # ========== SCRIPT 단계 피드백 처리 ==========
        if current_step == "script":
            if "확정" in feedback or "좋아" in feedback:
                return AgentResult(
                    success=True,
                    step="completed",
                    message="모든 기획이 완료되었습니다!\n\n저장된 내용:\n- 채널명\n- 캐릭터 이미지\n- 영상 아이디어\n- 대본",
                    data=self.context,
                )
            else:
                return await self._generate_script(
                    {"step": "script", "feedback": feedback, "regenerate": True}
                )

        # ========== 기본: 재생성 요청 ==========
        return await self.execute(
            {"step": current_step, "feedback": feedback, "regenerate": True}
        )

    async def process_auto_next(self, next_step: str) -> AgentResult:
        """프론트에서 auto_next 플래그 받으면 호출"""
        if next_step == "video_ideas":
            self.current_step = 2
            return await self.execute({"step": "video_ideas"})
        return AgentResult(success=False, message="Unknown next step")

    async def _generate_channel_name(self, input_data: Dict) -> AgentResult:
        """기존 채널명 생성 (레거시 호환)"""
        self.status = AgentStatus.RUNNING

        user_request = input_data.get("user_request", "경제/투자 관련 채널")
        feedback = input_data.get("feedback", "")

        prompt = PROMPTS["channel_name"].format(
            user_request=f"{user_request}\n추가 요청: {feedback}"
            if feedback
            else user_request
        )

        try:
            response = await llm_service.generate(prompt, temperature=0.8)
            data = extract_json(response)

            if not data or "channel_names" not in data:
                data = {
                    "channel_names": ["채널1", "채널2", "채널3"],
                    "reasoning": "기본",
                }

            self.set_context("channel_names", data["channel_names"])
            self.status = AgentStatus.WAITING_FEEDBACK

            names_list = data["channel_names"]

            return AgentResult(
                success=True,
                step="channel_name",
                message="채널명을 추천해드릴게요! 원하는 번호를 클릭하거나 입력하세요:",
                data={
                    "channel_names": names_list,
                    "type": "selection",
                    "options": [
                        {"id": i + 1, "label": name}
                        for i, name in enumerate(names_list)
                    ],
                },
                needs_feedback=True,
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(success=False, message=f"채널명 생성 실패: {str(e)}")

    async def _generate_video_ideas(self, input_data: Dict) -> AgentResult:
        self.status = AgentStatus.RUNNING

        channel_name = self.get_context("selected_channel_name", "") or input_data.get(
            "selected_channel_name", "투자연구소"
        )
        channel_concept = input_data.get("channel_concept", "경제/투자 교육")
        user_topic = input_data.get("user_topic", "")

        if user_topic:
            prompt = f"""'{channel_name}' 채널에서 '{user_topic}' 주제로 만들 수 있는 독창적인 영상 아이디어 5개를 생성해줘.

요구사항:
- 클릭을 유도하는 제목
- 강력한 후킹 문장
- 구체적인 내용 요약

JSON 형식:
{{"ideas": [{{"title": "제목", "hook": "후킹문장", "summary": "내용요약"}}]}}"""
        else:
            prompt = PROMPTS["video_ideas"].format(
                channel_name=channel_name, channel_concept=channel_concept
            )

        try:
            response = await llm_service.generate(
                prompt, temperature=0.8, max_tokens=4096
            )
            data = extract_json(response)

            if not data or "ideas" not in data:
                data = {
                    "ideas": [
                        {
                            "title": "가짜 부자 vs 진짜 부자의 심리",
                            "hook": "당신은 어느 쪽?",
                            "summary": "부자의 심리 분석",
                        },
                        {
                            "title": "월급 300으로 1억 모으기",
                            "hook": "현실적 재테크",
                            "summary": "자산 형성 로드맵",
                        },
                        {
                            "title": "부자들이 말 안하는 것들",
                            "hook": "왜 침묵할까?",
                            "summary": "상위 1%의 비밀",
                        },
                    ]
                }

            self.set_context("video_ideas", data["ideas"])
            self.status = AgentStatus.WAITING_FEEDBACK

            ideas = data["ideas"][:10]
            options = [
                {
                    "id": i + 1,
                    "label": idea.get("title", ""),
                    "description": idea.get("hook", ""),
                }
                for i, idea in enumerate(ideas)
            ]

            topic_msg = f"'{user_topic}' 주제로 " if user_topic else ""

            return AgentResult(
                success=True,
                step="video_ideas",
                message=f"{topic_msg}영상 아이디어를 생성했어요! 원하는 번호를 선택하거나, 다른 주제를 입력해주세요:",
                data={"ideas": ideas, "type": "selection", "options": options},
                needs_feedback=True,
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(success=False, message=f"아이디어 생성 실패: {str(e)}")

    async def _generate_script(self, input_data: Dict) -> AgentResult:
        self.status = AgentStatus.RUNNING

        video_idea = self.get_context("selected_video_idea") or input_data.get(
            "selected_video_idea", {}
        )
        character_name = self.get_context("character_name", "닉")
        feedback = input_data.get("feedback", "")

        video_title = (
            video_idea.get("title", "가짜 부자의 심리")
            if isinstance(video_idea, dict)
            else str(video_idea)
        )

        prompt = PROMPTS["script"].format(
            video_title=video_title, character_name=character_name
        )

        if feedback:
            prompt += f"\n\n추가 요청사항: {feedback}"

        try:
            response = await llm_service.generate(
                prompt, temperature=0.7, max_tokens=8192
            )
            data = extract_json(response)

            if not data or "script" not in data:
                data = {
                    "script": {
                        "opening": "오프닝...",
                        "intro": "인트로...",
                        "body1": "본론1...",
                        "body2": "본론2...",
                        "body3": "본론3...",
                        "conclusion": "결론...",
                    },
                    "estimated_duration": "10-12분",
                }

            self.set_context("script", data["script"])
            self.status = AgentStatus.WAITING_FEEDBACK

            script = data["script"]

            def format_section(title, text, max_len=500):
                if not text:
                    return ""
                truncated = text[:max_len] + ("..." if len(text) > max_len else "")
                return f"**[{title}]** {truncated}\n\n"

            if isinstance(script, dict):
                parts = []
                if script.get("opening"):
                    parts.append(format_section("오프닝", script["opening"], 400))
                if script.get("intro"):
                    parts.append(format_section("인트로", script["intro"], 400))
                if script.get("body1"):
                    parts.append(format_section("본론1", script["body1"], 500))
                if script.get("body2"):
                    parts.append(format_section("본론2", script["body2"], 500))
                if script.get("body3"):
                    parts.append(format_section("본론3", script["body3"], 500))
                if script.get("conclusion"):
                    parts.append(format_section("결론+CTA", script["conclusion"], 400))
                script_display = "".join(parts) if parts else str(script)[:500]
            else:
                script_display = str(script)[:1500]

            est_dur = data.get("estimated_duration", "10-15분")

            return AgentResult(
                success=True,
                step="script",
                message=f"대본을 작성했어요:\n\n{script_display}---\n**예상 분량:** {est_dur}\n\n확정을 입력하면 완료됩니다. 수정이 필요하면 요청해주세요.",
                data=data,
                needs_feedback=True,
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(success=False, message=f"대본 작성 실패: {str(e)}")
