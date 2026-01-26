import json
import sys
import re
sys.path.append('/data/routine/routine-studio-v2')

from typing import Dict, Any, List, Optional
from agents.base import BaseAgent, AgentResult, AgentStatus
from apps.api.services.llm import llm_service
from .prompts import PROMPTS

def extract_json(text: str) -> Optional[Dict]:
    if '{' in text:
        start = text.find('{')
        end = text.rfind('}') + 1
        json_str = text[start:end]
        try:
            return json.loads(json_str)
        except:
            json_str = json_str.replace('\n', '\\n')
            try:
                return json.loads(json_str)
            except:
                pass
    return None

class PlannerAgent(BaseAgent):
    STEPS = ['channel_name', 'character', 'video_ideas', 'script']
    
    def __init__(self):
        super().__init__('PlannerAgent')
        self.current_step = 0
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        step = input_data.get('step', self.STEPS[self.current_step])
        
        if step == 'channel_name':
            return await self._generate_channel_name(input_data)
        elif step == 'character':
            return AgentResult(
                success=True,
                step='character',
                message='캐릭터 생성을 시작합니다.',
                data={'next_agent': 'CharacterAgent'},
                needs_feedback=False
            )
        elif step == 'video_ideas':
            return await self._generate_video_ideas(input_data)
        elif step == 'script':
            return await self._generate_script(input_data)
        
        return AgentResult(success=False, message=f'알 수 없는 단계: {step}')
    
    async def handle_feedback(self, feedback: str, images: List[str] = None) -> AgentResult:
        current_step = self.STEPS[self.current_step]
        
        if '확정' in feedback or '좋아' in feedback or '이걸로' in feedback:
            self.current_step += 1
            if self.current_step < len(self.STEPS):
                return await self.execute({'step': self.STEPS[self.current_step]})
            else:
                return AgentResult(
                    success=True,
                    step='completed',
                    message='모든 기획 단계가 완료되었습니다!',
                    data=self.context
                )
        else:
            return await self.execute({
                'step': current_step,
                'feedback': feedback,
                'regenerate': True
            })
    
    async def _generate_channel_name(self, input_data: Dict) -> AgentResult:
        self.status = AgentStatus.RUNNING
        
        user_request = input_data.get('user_request', '경제/투자 관련 채널')
        feedback = input_data.get('feedback', '')
        
        prompt = PROMPTS['channel_name'].format(
            user_request=f'{user_request}\n추가 요청: {feedback}' if feedback else user_request
        )
        
        try:
            response = await llm_service.generate(prompt, temperature=0.8)
            data = extract_json(response)
            
            if not data or 'channel_names' not in data:
                data = {'channel_names': ['채널1', '채널2', '채널3'], 'reasoning': '기본'}
            
            self.set_context('channel_names', data['channel_names'])
            self.status = AgentStatus.WAITING_FEEDBACK
            
            # 클릭 가능한 형태로 포맷
            names_list = data['channel_names']
            
            return AgentResult(
                success=True,
                step='channel_name',
                message='채널명을 추천해드릴게요! 원하는 번호를 클릭하거나 입력하세요:',
                data={
                    'channel_names': names_list,
                    'type': 'selection',
                    'options': [{'id': i+1, 'label': name} for i, name in enumerate(names_list)]
                },
                needs_feedback=True
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(success=False, message=f'채널명 생성 실패: {str(e)}')
    
    async def _generate_video_ideas(self, input_data: Dict) -> AgentResult:
        self.status = AgentStatus.RUNNING
        
        channel_name = self.get_context('selected_channel_name', '') or input_data.get('selected_channel_name', '투자연구소')
        channel_concept = input_data.get('channel_concept', '경제/투자 교육')
        
        prompt = PROMPTS['video_ideas'].format(
            channel_name=channel_name,
            channel_concept=channel_concept
        )
        
        try:
            response = await llm_service.generate(prompt, temperature=0.8, max_tokens=4096)
            data = extract_json(response)
            
            if not data or 'ideas' not in data:
                data = {
                    'ideas': [
                        {'title': '가짜 부자 vs 진짜 부자의 심리', 'hook': '당신은 어느 쪽?', 'summary': '부자의 심리 분석'},
                        {'title': '월급 300으로 1억 모으기', 'hook': '현실적 재테크', 'summary': '자산 형성 로드맵'},
                        {'title': '부자들이 말 안하는 것들', 'hook': '왜 침묵할까?', 'summary': '상위 1%의 비밀'}
                    ]
                }
            
            self.set_context('video_ideas', data['ideas'])
            self.status = AgentStatus.WAITING_FEEDBACK
            
            ideas = data['ideas'][:10]
            options = [{'id': i+1, 'label': idea.get('title', ''), 'description': idea.get('hook', '')} for i, idea in enumerate(ideas)]
            
            return AgentResult(
                success=True,
                step='video_ideas',
                message='영상 아이디어를 생성했어요! 원하는 번호를 선택하세요:',
                data={
                    'ideas': ideas,
                    'type': 'selection',
                    'options': options
                },
                needs_feedback=True
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(success=False, message=f'아이디어 생성 실패: {str(e)}')
    
    async def _generate_script(self, input_data: Dict) -> AgentResult:
        self.status = AgentStatus.RUNNING
        
        video_idea = self.get_context('selected_video_idea') or input_data.get('selected_video_idea', {})
        character_name = self.get_context('character_name', '닉')
        
        video_title = video_idea.get('title', '가짜 부자의 심리') if isinstance(video_idea, dict) else str(video_idea)
        
        prompt = PROMPTS['script'].format(
            video_title=video_title,
            character_name=character_name
        )
        
        try:
            response = await llm_service.generate(prompt, temperature=0.7, max_tokens=8192)
            data = extract_json(response)
            
            if not data or 'script' not in data:
                data = {
                    'script': {
                        'opening': '오프닝...',
                        'intro': '인트로...',
                        'body1': '본론1...',
                        'body2': '본론2...',
                        'body3': '본론3...',
                        'conclusion': '결론...'
                    },
                    'estimated_duration': '10-12분'
                }
            
            self.set_context('script', data['script'])
            self.status = AgentStatus.WAITING_FEEDBACK
            
            script = data['script']
            opening = script.get('opening', '')[:300] if isinstance(script, dict) else str(script)[:300]
            
            return AgentResult(
                success=True,
                step='script',
                message=f'대본을 작성했어요:\n\n**[오프닝]**\n{opening}...\n\n"확정"을 입력하면 완료됩니다.',
                data=data,
                needs_feedback=True
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(success=False, message=f'대본 작성 실패: {str(e)}')
