import json
import sys
import os
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

sys.path.append('/data/routine/routine-studio-v2')

from agents.base import AgentResult, AgentStatus
from agents.planner.agent import PlannerAgent
from agents.character.agent import CharacterAgent
from agents.benchmarker.agent import BenchmarkerAgent
from agents.voiceover.agent import VoiceoverAgent
from agents.image_prompter.agent import ImagePrompterAgent
from agents.image_generator.agent import ImageGeneratorAgent
from agents.composer.agent import ComposerAgent
from apps.api.services.vision import vision_service
from apps.api.services.llm import llm_service
from agents.image_utils import optimize_image

SESSIONS_DIR = Path('/data/routine/routine-studio-v2/output/.sessions')
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class WorkflowStep(Enum):
    CHANNEL_NAME = 'channel_name'
    BENCHMARKING = 'benchmarking'
    CHARACTER = 'character'
    TTS_SETTINGS = 'tts_settings'
    VIDEO_IDEAS = 'video_ideas'
    SCRIPT = 'script'
    IMAGE_PROMPT = 'image_prompt'
    IMAGE_GENERATE = 'image_generate'
    VOICEOVER = 'voiceover'
    COMPOSE = 'compose'  # NEW: 영상+음성+자막 합성
    COMPLETED = 'completed'


@dataclass
class Session:
    id: str
    current_step: WorkflowStep = WorkflowStep.CHANNEL_NAME
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'current_step': self.current_step.value,
            'context': self.context,
            'history': self.history
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Session':
        return cls(
            id=data['id'],
            current_step=WorkflowStep(data['current_step']),
            context=data.get('context', {}),
            history=data.get('history', [])
        )


def save_session(session: Session):
    path = SESSIONS_DIR / f'{session.id}.json'
    with open(path, 'w') as f:
        json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)


def load_session(session_id: str) -> Optional[Session]:
    path = SESSIONS_DIR / f'{session_id}.json'
    if path.exists():
        with open(path) as f:
            return Session.from_dict(json.load(f))
    return None


class Orchestrator:
    STEP_ORDER = [
        WorkflowStep.CHANNEL_NAME,
        WorkflowStep.BENCHMARKING,
        WorkflowStep.CHARACTER,
        WorkflowStep.TTS_SETTINGS,
        WorkflowStep.VIDEO_IDEAS,
        WorkflowStep.SCRIPT,
        WorkflowStep.IMAGE_PROMPT,
        WorkflowStep.IMAGE_GENERATE,
        WorkflowStep.VOICEOVER,
        WorkflowStep.COMPOSE,  # NEW
        WorkflowStep.COMPLETED
    ]

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.planner = PlannerAgent()
        self.character_agent = CharacterAgent()
        self.benchmarker_agents: Dict[str, BenchmarkerAgent] = {}
        self.voiceover_agent = VoiceoverAgent()
        self.image_prompter_agent = ImagePrompterAgent()
        self.image_generator_agent = ImageGeneratorAgent()
        self.composer_agent = ComposerAgent()  # NEW

    def get_or_create_session(self, session_id: str) -> Session:
        if session_id in self.sessions:
            return self.sessions[session_id]

        session = load_session(session_id)
        if session:
            self.sessions[session_id] = session
            for key in ['channel_names', 'selected_channel_name', 'video_ideas', 'selected_video_idea', 'benchmark_report']:
                if key in session.context:
                    self.planner.set_context(key, session.context[key])
            return session

        session = Session(id=session_id)
        self.sessions[session_id] = session
        return session

    def _save(self, session: Session):
        save_session(session)

    def _get_current_agent(self, step: WorkflowStep, session_id: str = None):
        if step == WorkflowStep.CHARACTER:
            return self.character_agent
        elif step == WorkflowStep.BENCHMARKING:
            if session_id and session_id not in self.benchmarker_agents:
                self.benchmarker_agents[session_id] = BenchmarkerAgent()
            return self.benchmarker_agents.get(session_id, BenchmarkerAgent())
        elif step == WorkflowStep.IMAGE_PROMPT:
            return self.image_prompter_agent
        elif step == WorkflowStep.IMAGE_GENERATE:
            return self.image_generator_agent
        elif step == WorkflowStep.VOICEOVER:
            return self.voiceover_agent
        elif step == WorkflowStep.COMPOSE:
            return self.composer_agent
        return self.planner

    def _extract_number(self, message: str) -> Optional[int]:
        if message.strip().isdigit():
            return int(message.strip())

        match = re.search(r'(\d+)\s*번', message)
        if match:
            return int(match.group(1))

        korean_nums = {'첫': 1, '두': 2, '세': 3, '네': 4, '다섯': 5,
                       '여섯': 6, '일곱': 7, '여덟': 8, '아홉': 9, '열': 10}
        for k, v in korean_nums.items():
            if k in message:
                return v

        return None

    def _is_confirmation(self, message: str) -> bool:
        confirmations = ['확정', '좋아', '이걸로', '다음', 'ok', 'OK', '완료', '할께', '할게', '확인']
        return any(c in message for c in confirmations)

    def _is_selection(self, message: str) -> bool:
        return self._extract_number(message) is not None

    async def _format_character_intro(self, char_info: dict, context: dict = None) -> str:
        """캐릭터와 채널의 스토리텔링 소개"""
        if not char_info:
            return ""

        channel_name = context.get("selected_channel_name", "") if context else ""
        user_request = context.get("user_request", "") if context else ""

        # 캐릭터 정보 추출
        char_type = char_info.get("character_type", "")
        gender = char_info.get("gender", "")
        clothing = char_info.get("clothing", "")
        expression = char_info.get("expression", "")
        art_style = char_info.get("art_style", "")
        personality = char_info.get("personality_vibe", "")

        # 성별/타입 한국어 변환
        if char_type == "human":
            char_kr = "여성" if gender == "female" else "남성" if gender == "male" else ""
        elif char_type == "animal":
            char_kr = "귀여운 동물"
        elif char_type == "fantasy":
            char_kr = "판타지"
        else:
            char_kr = ""

        # 스토리텔링 메시지 생성
        lines = []

        if channel_name:
            lines.append(f"**{channel_name}** 채널의 얼굴이 될 캐릭터를 만났어요!")
        else:
            lines.append("채널의 얼굴이 될 캐릭터를 만났어요!")

        # 캐릭터 설명 (줄바꿈 2번)
        desc_parts = []
        if char_kr:
            desc_parts.append(char_kr)
        if clothing:
            desc_parts.append(clothing)
        if expression:
            desc_parts.append(f"{expression} 표정")

        if desc_parts:
            lines.append("")
            lines.append(f"**캐릭터:** {', '.join(desc_parts)}")

        if art_style:
            lines.append("")
            lines.append(f"**스타일:** {art_style}")

        # 스토리 제안 생성 (LLM 사용)
        lines.append("")
        story_suggestion = await self._generate_story_suggestion(char_info, channel_name, user_request)
        if story_suggestion:
            lines.append(f"{story_suggestion}")

        return "\n".join(lines)

    async def _generate_story_suggestion(self, char_info: dict, channel_name: str, user_request: str) -> str:
        """LLM으로 위트있는 스토리 제안 생성"""

        # 캐릭터 정보 정리
        char_desc_parts = []
        if char_info.get("gender"):
            char_desc_parts.append(char_info["gender"])
        if char_info.get("character_type"):
            char_desc_parts.append(char_info["character_type"])
        if char_info.get("clothing"):
            char_desc_parts.append(char_info["clothing"])
        if char_info.get("expression"):
            char_desc_parts.append(char_info["expression"])
        if char_info.get("personality_vibe"):
            char_desc_parts.append(char_info["personality_vibe"])

        char_desc = ", ".join(char_desc_parts) if char_desc_parts else "캐릭터"

        prompt = f"""유튜브 채널 캐릭터 소개 멘트를 작성해주세요.

채널명: {channel_name or '(미정)'}
채널 주제: {user_request or '(미정)'}
캐릭터: {char_desc}

요청사항:
1. 캐릭터와 채널 컨셉을 연결하는 짧은 스토리/역할 제안
2. 위트있고 재미있게 작성
3. 1-2문장으로 간결하게
4. "~하면 좋을 것 같아요!" 형식으로 끝내기
5. 캐릭터에게 귀여운 별명이나 역할을 부여해도 좋음

예시:
- "이 캐릭터가 '월급쟁이 구원자'로 변신해서 직장인들의 재테크 고민을 해결해주면 딱이겠어요!"
- "밤마다 나타나 게임 꿀팁을 전수하는 '미드나잇 게이머' 콘셉트로 가면 좋을 것 같아요!"
- "요리하다 실수해도 웃으면서 넘기는 '실패해도 맛있는 셰프' 캐릭터로 만들면 친근할 것 같아요!"

스토리 제안 (1-2문장만):"""

        try:
            response = await llm_service.generate(prompt, max_tokens=150)
            suggestion = response.strip()

            # 따옴표나 불필요한 prefix 제거
            suggestion = suggestion.strip('"\'')
            if suggestion.startswith("- "):
                suggestion = suggestion[2:]

            return suggestion
        except Exception as e:
            print(f"[Orchestrator] Story suggestion failed: {e}")
            # 폴백: 간단한 기본 메시지
            if channel_name:
                return f"**{channel_name}** 채널의 매력적인 진행자로 활약할 준비가 되었어요!"
            return "이 캐릭터로 멋진 콘텐츠를 만들어볼게요!"

    async def start(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        session = self.get_or_create_session(session_id)
        session.context['user_request'] = input_data.get('user_request', '')

        result = await self.planner.execute({
            'step': 'channel_name',
            'user_request': input_data.get('user_request', '')
        })

        if result.data and 'channel_names' in result.data:
            session.context['channel_names'] = result.data['channel_names']

        self._save(session)
        return self._format_response(session, result)

    async def process_message(self, session_id: str, message: str, images: List[str] = None) -> Dict[str, Any]:
        session = self.get_or_create_session(session_id)
        current_step = session.current_step

        # 스킵 처리
        if '스킵' in message or 'skip' in message.lower():
            result = await self._handle_skip(session)
            self._save(session)
            return self._format_response(session, result)

        # ========== CHARACTER 단계에서 이미지 + 확정 처리 ==========
        if current_step == WorkflowStep.CHARACTER and images and len(images) > 0:
            if self._is_confirmation(message):
                img = images[0]
                if img.startswith('data:'):
                    img = img.split(',', 1)[1]

                char_intro = ''
                try:
                    char_info = await vision_service.describe_character_with_thinking(img)
                    char_intro = await self._format_character_intro(char_info, session.context)
                    session.context['character_info'] = char_info  # 캐릭터 정보 저장
                except Exception as e:
                    print(f'[Orchestrator] Character analysis failed: {e}')
                    char_intro = ''

                optimized_image = optimize_image(images[0])
                session.context['character_image'] = optimized_image
                self.character_agent.set_context('character_image', optimized_image)

                session.context['character_confirmed'] = True
                self._save(session)

                if char_intro:
                    result_message = f'{char_intro}\n\n다음 단계로 진행하려면 아무 메시지나 입력해주세요.'
                else:
                    result_message = '캐릭터 이미지를 저장했습니다.\n\n다음 단계로 진행하려면 아무 메시지나 입력해주세요.'

                return {
                    'session_id': session.id,
                    'current_step': 'character_confirmed',
                    'message': result_message,
                    'images': images,
                    'needs_feedback': True,
                    'data': {'character_image': optimized_image, 'pending_next_step': 'video_ideas'},
                    'success': True,
                    'context': session.context
                }

        # ========== CHARACTER 확정 후 TTS_SETTINGS로 진행 ==========
        if current_step == WorkflowStep.CHARACTER and session.context.get('character_confirmed'):
            session.context.pop('character_confirmed', None)
            session.current_step = WorkflowStep.TTS_SETTINGS
            
            # TTS 설정 메시지
            tts_message = """캐릭터가 확정되었습니다! 이제 음성 설정을 해주세요.

**음성 옵션을 선택해주세요:**

1️⃣ **기본 보이스 (Sohee)**
   - 한국어에 최적화된 따뜻한 여성 음성
   - 바로 사용 가능

2️⃣ **보이스 클로닝**
   - 원하는 목소리로 복제하여 사용
   - YouTube 영상 또는 저장된 샘플 사용

번호를 입력해주세요. (1 또는 2)"""
            
            await self.save_session(session, session_id)
            return AgentResult(
                success=True,
                step="tts_settings",
                message=tts_message,
                needs_feedback=True,
                data={"type": "selection", "options": [
                    {"id": 1, "label": "기본 보이스 (Sohee)"},
                    {"id": 2, "label": "보이스 클로닝"}
                ]}
            )

            result = await self.planner.execute({
                'step': 'video_ideas',
                **session.context
            })

            if result.data and 'ideas' in result.data:
                session.context['video_ideas'] = result.data['ideas']

            self._save(session)
            return self._format_response(session, result)


        # ========== TTS_SETTINGS 단계 처리 ==========
        if current_step == WorkflowStep.TTS_SETTINGS:
            msg_lower = message.lower().strip()
            
            # 클로닝 모드 진입
            if session.context.get('tts_clone_mode'):
                clone_mode = session.context.get('tts_clone_mode')
                
                # YouTube URL 입력 대기 중
                if clone_mode == 'youtube' and not session.context.get('tts_youtube_url'):
                    if 'youtube.com' in message or 'youtu.be' in message:
                        session.context['tts_youtube_url'] = message.strip()
                        await self.save_session(session, session_id)
                        return AgentResult(
                            success=True,
                            step="tts_settings",
                            message="YouTube URL이 저장되었습니다. 음성을 추출할 시간대를 입력해주세요.\n예: 0:30-0:45 (30초~45초 구간)",
                            needs_feedback=True
                        )
                    else:
                        return AgentResult(
                            success=True,
                            step="tts_settings",
                            message="올바른 YouTube URL을 입력해주세요.\n예: https://youtube.com/watch?v=...",
                            needs_feedback=True
                        )
                
                # YouTube 시간대 입력 대기 중
                if clone_mode == 'youtube' and session.context.get('tts_youtube_url') and not session.context.get('tts_youtube_time'):
                    session.context['tts_youtube_time'] = message.strip()
                    session.context['tts_voice_option'] = 'youtube'
                    session.current_step = WorkflowStep.VIDEO_IDEAS
                    await self.save_session(session, session_id)
                    
                    channel_name = session.context.get('channel_name', '채널')
                    complete_msg = f"""음성 설정이 완료되었습니다!
- 방식: YouTube 보이스 클로닝
- URL: {session.context.get('tts_youtube_url')}
- 구간: {message.strip()}

**{channel_name}** 채널 설정이 완료되었습니다!

이제 어떤 주제의 영상을 만들까요? 주제나 아이디어를 입력해주세요."""
                    return AgentResult(
                        success=True,
                        step="video_ideas",
                        message=complete_msg,
                        needs_feedback=True
                    )
                
                # 샘플 선택 대기 중
                if clone_mode == 'sample':
                    try:
                        sample_idx = int(message.strip()) - 1
                        session.context['tts_sample_idx'] = sample_idx
                        session.context['tts_voice_option'] = 'sample'
                        session.current_step = WorkflowStep.VIDEO_IDEAS
                        await self.save_session(session, session_id)
                        
                        channel_name = session.context.get('channel_name', '채널')
                        complete_msg = f"""음성 설정이 완료되었습니다!
- 방식: 저장된 샘플 사용

**{channel_name}** 채널 설정이 완료되었습니다!

이제 어떤 주제의 영상을 만들까요? 주제나 아이디어를 입력해주세요."""
                        return AgentResult(
                            success=True,
                            step="video_ideas",
                            message=complete_msg,
                            needs_feedback=True
                        )
                    except:
                        return AgentResult(
                            success=True,
                            step="tts_settings",
                            message="올바른 번호를 입력해주세요.",
                            needs_feedback=True
                        )
            
            # 1번 선택: 기본 보이스
            if msg_lower in ['1', '기본', 'default', 'sohee']:
                session.context['tts_voice_option'] = 'default'
                session.context['tts_speaker'] = 'Sohee'
                session.current_step = WorkflowStep.VIDEO_IDEAS
                await self.save_session(session, session_id)
                
                channel_name = session.context.get('channel_name', '채널')
                complete_msg = f"""음성 설정이 완료되었습니다!
- 음성: 기본 보이스 (Sohee)

**{channel_name}** 채널 설정이 완료되었습니다!

이제 어떤 주제의 영상을 만들까요? 주제나 아이디어를 입력해주세요."""
                return AgentResult(
                    success=True,
                    step="video_ideas",
                    message=complete_msg,
                    needs_feedback=True
                )
            
            # 2번 선택: 보이스 클로닝
            if msg_lower in ['2', '클로닝', 'clone', 'cloning']:
                clone_msg = """**보이스 클로닝 방식을 선택해주세요:**

1️⃣ **YouTube 영상에서 추출**
   - 원하는 유튜버의 목소리 복제
   - URL과 시간대 입력 필요

2️⃣ **저장된 샘플 사용**
   - 미리 준비된 음성 샘플 선택

번호를 입력해주세요. (1 또는 2)"""
                return AgentResult(
                    success=True,
                    step="tts_settings",
                    message=clone_msg,
                    needs_feedback=True,
                    data={"type": "selection", "options": [
                        {"id": 1, "label": "YouTube에서 추출"},
                        {"id": 2, "label": "저장된 샘플"}
                    ]}
                )
            
            # 클로닝 하위 옵션
            if session.context.get('tts_voice_option') is None:
                if msg_lower == '1' or 'youtube' in msg_lower or 'yt' in msg_lower:
                    session.context['tts_clone_mode'] = 'youtube'
                    await self.save_session(session, session_id)
                    return AgentResult(
                        success=True,
                        step="tts_settings",
                        message="복제할 목소리가 있는 YouTube 영상 URL을 입력해주세요.\n예: https://youtube.com/watch?v=...",
                        needs_feedback=True
                    )
                elif msg_lower == '2' or '샘플' in msg_lower or 'sample' in msg_lower:
                    session.context['tts_clone_mode'] = 'sample'
                    await self.save_session(session, session_id)
                    return AgentResult(
                        success=True,
                        step="tts_settings",
                        message="저장된 샘플 목록:\n(샘플 기능은 아직 준비 중입니다. 기본 보이스를 사용하려면 '1'을 입력해주세요.)",
                        needs_feedback=True
                    )
            
            # 잘못된 입력
            return AgentResult(
                success=True,
                step="tts_settings",
                message="1 또는 2를 입력해주세요.",
                needs_feedback=True
            )

        # ========== VIDEO_IDEAS 단계에서 새 주제 입력 처리 ==========
        if current_step == WorkflowStep.VIDEO_IDEAS:
            num = self._extract_number(message)
            if num is not None:
                ideas = session.context.get('video_ideas', [])
                if 0 < num <= len(ideas):
                    session.context['selected_video_idea'] = ideas[num - 1]
                    self.planner.set_context('selected_video_idea', ideas[num - 1])

                    session.current_step = WorkflowStep.SCRIPT
                    result = await self.planner.execute({
                        'step': 'script',
                        **session.context
                    })

                    if result.data and 'script' in result.data:
                        session.context['script'] = result.data['script']

                    self._save(session)
                    return self._format_response(session, result)

            if self._is_confirmation(message):
                ideas = session.context.get('video_ideas', [])
                if ideas:
                    session.context['selected_video_idea'] = ideas[0]
                    self.planner.set_context('selected_video_idea', ideas[0])

                    session.current_step = WorkflowStep.SCRIPT
                    result = await self.planner.execute({
                        'step': 'script',
                        **session.context
                    })

                    if result.data and 'script' in result.data:
                        session.context['script'] = result.data['script']

                    self._save(session)
                    return self._format_response(session, result)

            if len(message) > 5 and not self._is_confirmation(message) and not self._is_selection(message):
                result = await self.planner.execute({
                    'step': 'video_ideas',
                    'user_topic': message,
                    **session.context
                })

                if result.data and 'ideas' in result.data:
                    session.context['video_ideas'] = result.data['ideas']

                self._save(session)
                return self._format_response(session, result)

        # ========== CHANNEL_NAME 단계: planner agent로 위임 (설문 처리) ==========
        if current_step == WorkflowStep.CHANNEL_NAME:
            # 채널명이 이미 선택되었고 "확인" 입력 시 다음 단계로
            if session.context.get('selected_channel_name') and self._is_confirmation(message):
                session.current_step = WorkflowStep.BENCHMARKING
                benchmarker = self._get_current_agent(WorkflowStep.BENCHMARKING, session_id)
                bench_result = await benchmarker.execute({
                    'step': 'benchmarking',
                    **session.context
                })
                self._save(session)
                return self._format_response(session, bench_result)

            result = await self.planner.handle_feedback(message, images)

            # 채널명 확정 시 context에 저장
            if result.step == 'channel_name_confirmed' and result.data and result.data.get('selected_channel_name'):
                session.context['selected_channel_name'] = result.data['selected_channel_name']
                self.planner.set_context('selected_channel_name', result.data['selected_channel_name'])

                # needs_feedback가 False면 바로 다음 단계로
                if not result.needs_feedback:
                    session.current_step = WorkflowStep.BENCHMARKING
                    benchmarker = self._get_current_agent(WorkflowStep.BENCHMARKING, session_id)
                    bench_result = await benchmarker.execute({
                        'step': 'benchmarking',
                        **session.context
                    })
                    self._save(session)
                    return self._format_response(session, bench_result)

            self._save(session)
            return self._format_response(session, result)

        # ========== 숫자 선택 처리 (BENCHMARKING, CHANNEL_NAME 제외) ==========
        if current_step not in [WorkflowStep.BENCHMARKING, WorkflowStep.CHANNEL_NAME]:
            num = self._extract_number(message)
            if num is not None:
                result = await self._handle_selection(session, num)
                self._save(session)
                return self._format_response(session, result)

        # ========== 확정 처리 (BENCHMARKING, CHANNEL_NAME 제외) ==========
        if current_step not in [WorkflowStep.BENCHMARKING, WorkflowStep.CHANNEL_NAME] and self._is_confirmation(message):
            result = await self._handle_next_step(session)
            self._save(session)
            return self._format_response(session, result)

        # ========== BENCHMARKING 완료 후 "다음" 입력 시 먼저 처리 (버그 수정) ==========
        if current_step == WorkflowStep.BENCHMARKING and session.context.get("benchmark_shown"):
            if self._is_confirmation(message):
                session.current_step = WorkflowStep.CHARACTER
                char_result = await self.character_agent.execute({
                    "step": "character",
                    **session.context
                })
                self._save(session)
                return self._format_response(session, char_result)

        # ========== 기본 피드백 처리 ==========
        agent = self._get_current_agent(current_step, session_id)
        result = await agent.handle_feedback(message, images)

        # 벤치마킹 완료 처리
        if current_step == WorkflowStep.BENCHMARKING:
            # 다시 분석 요청 시 benchmark_shown 초기화
            if result.step in ['benchmark_confirm', 'benchmark_collect']:
                session.context.pop('benchmark_shown', None)
                session.context.pop('benchmark_report', None)

            if result.data:
                if result.data.get('skipped'):
                    session.current_step = WorkflowStep.CHARACTER
                    char_result = await self.character_agent.execute({
                        'step': 'character',
                        **session.context
                    })
                    self._save(session)
                    return self._format_response(session, char_result)

                if result.data.get('report') and not result.needs_feedback:
                    session.context['benchmark_report'] = result.data['report']
                    session.context['benchmark_shown'] = True
                    result.message = result.message + "\n\n---\n\n**리포트 확인 완료!**\n다음 단계로 진행하려면 확인 또는 다음을 입력하세요."
                    result.needs_feedback = True
                    self._save(session)
                    return self._format_response(session, result)

                # 벤치마킹 완료 후 "다음/확인" 입력 시 캐릭터로 진행
                if session.context.get('benchmark_shown'):
                    # 사용자가 "다음" 또는 "확인"을 입력한 경우
                    if self._is_confirmation(message) or result.step == 'benchmark_complete':
                        session.current_step = WorkflowStep.CHARACTER
                        char_result = await self.character_agent.execute({
                            'step': 'character',
                            **session.context
                        })
                        self._save(session)
                        return self._format_response(session, char_result)

        # ========== CHARACTER 단계에서 character_confirmed 처리 ==========
        if current_step == WorkflowStep.CHARACTER and result.step == 'character_confirmed':
            # 스토리텔링 포맷 적용
            char_info = result.data.get('character_analysis', {}) if result.data else {}
            if char_info:
                try:
                    char_intro = await self._format_character_intro(char_info, session.context)
                    if char_intro:
                        result.message = char_intro
                        session.context['character_info'] = char_info
                except Exception as e:
                    print(f'[Orchestrator] Character intro formatting failed: {e}')

        # IMAGE_GENERATE 완료 후 데이터 저장
        if current_step == WorkflowStep.IMAGE_GENERATE:
            if result.data:
                if result.data.get('images'):
                    session.context['generated_images'] = result.data['images']
                if result.data.get('videos'):
                    session.context['generated_videos'] = result.data['videos']
                if result.data.get('qc_results'):
                    session.context['qc_results'] = result.data['qc_results']

        # VOICEOVER 완료 후 데이터 저장
        if current_step == WorkflowStep.VOICEOVER:
            if result.data:
                if result.data.get('sections'):
                    session.context['voice_sections'] = result.data['sections']

        self._save(session)
        return self._format_response(session, result)

    async def _handle_selection(self, session: Session, num: int) -> AgentResult:
        current_step = session.current_step

        if current_step == WorkflowStep.CHANNEL_NAME:
            names = session.context.get('channel_names', [])
            if 0 < num <= len(names):
                session.context['selected_channel_name'] = names[num - 1]
                self.planner.set_context('selected_channel_name', names[num - 1])

        elif current_step == WorkflowStep.VIDEO_IDEAS:
            ideas = session.context.get('video_ideas', [])
            if 0 < num <= len(ideas):
                session.context['selected_video_idea'] = ideas[num - 1]
                self.planner.set_context('selected_video_idea', ideas[num - 1])

        return await self._handle_next_step(session)

    async def _handle_next_step(self, session: Session) -> AgentResult:
        current_step = session.current_step
        next_idx = self.STEP_ORDER.index(current_step) + 1

        if next_idx >= len(self.STEP_ORDER):
            return self._complete_result(session)

        session.current_step = self.STEP_ORDER[next_idx]

        if session.current_step == WorkflowStep.COMPLETED:
            return self._complete_result(session)

        agent = self._get_current_agent(session.current_step, session.id)

        # 각 에이전트에 필요한 데이터 전달
        input_data = {
            'step': session.current_step.value,
            'session_id': session.id,
            **session.context
        }

        # IMAGE_GENERATE 에이전트에 프롬프트 전달
        if session.current_step == WorkflowStep.IMAGE_GENERATE:
            input_data['prompts'] = session.context.get('image_prompts', {}).get('prompts', [])
            input_data['generate_videos'] = True
            input_data['enable_qc'] = True

        # COMPOSE 에이전트에 비디오/오디오 데이터 전달
        if session.current_step == WorkflowStep.COMPOSE:
            input_data['videos'] = session.context.get('generated_videos', [])
            input_data['audios'] = session.context.get('voice_sections', [])
            input_data['prompts'] = session.context.get('image_prompts', {}).get('prompts', [])

        result = await agent.execute(input_data)

        if result.data:
            if 'ideas' in result.data:
                session.context['video_ideas'] = result.data['ideas']
            if 'script' in result.data:
                session.context['script'] = result.data['script']
            if 'prompts' in result.data:
                session.context['image_prompts'] = result.data
            if 'images' in result.data:
                session.context['generated_images'] = result.data['images']
            if 'videos' in result.data:
                session.context['generated_videos'] = result.data['videos']
            if 'report' in result.data:
                session.context['benchmark_report'] = result.data['report']
            if 'sections' in result.data:
                session.context['voice_sections'] = result.data['sections']
            if 'final_video' in result.data:
                session.context['final_video'] = result.data['final_video']
            if 'subtitle_file' in result.data:
                session.context['subtitle_file'] = result.data['subtitle_file']

        return result

    async def _handle_skip(self, session: Session) -> AgentResult:
        return await self._handle_next_step(session)

    def _complete_result(self, session: Session) -> AgentResult:
        channel = session.context.get('selected_channel_name', '')
        idea = session.context.get('selected_video_idea', {})
        idea_title = idea.get('title', '') if isinstance(idea, dict) else str(idea)
        has_benchmark = 'benchmark_report' in session.context
        final_video = session.context.get('final_video', '')

        msg = f"""**영상 제작이 완료되었습니다!**

**채널명:** {channel}
**영상 주제:** {idea_title}
"""
        if has_benchmark:
            msg += '**벤치마킹:** 완료\n'

        if final_video:
            msg += f'\n**최종 영상:** `{Path(final_video).name}`'
            msg += f'\n**저장 위치:** `{Path(final_video).parent}`'

        return AgentResult(
            success=True,
            step='completed',
            message=msg,
            data=session.context
        )

    def _format_response(self, session: Session, result: AgentResult) -> Dict[str, Any]:
        return {
            'session_id': session.id,
            'current_step': session.current_step.value,
            'message': result.message,
            'images': result.images,
            'needs_feedback': result.needs_feedback,
            'data': result.data,
            'success': result.success,
            'context': session.context
        }


orchestrator = Orchestrator()
