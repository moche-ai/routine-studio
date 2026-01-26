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

SESSIONS_DIR = Path('/data/routine/routine-studio-v2/output/.sessions')
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

class WorkflowStep(Enum):
    CHANNEL_NAME = 'channel_name'
    BENCHMARKING = 'benchmarking'  # 벤치마킹 단계 추가
    CHARACTER = 'character'
    VIDEO_IDEAS = 'video_ideas'
    SCRIPT = 'script'
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
        WorkflowStep.BENCHMARKING,  # 채널명 다음에 벤치마킹
        WorkflowStep.CHARACTER,
        WorkflowStep.VIDEO_IDEAS,
        WorkflowStep.SCRIPT,
        WorkflowStep.COMPLETED
    ]
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.planner = PlannerAgent()
        self.character_agent = CharacterAgent()
        # 세션별 벤치마커 에이전트 저장
        self.benchmarker_agents: Dict[str, BenchmarkerAgent] = {}
    
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
            # 세션별로 새 벤치마커 에이전트 생성
            if session_id and session_id not in self.benchmarker_agents:
                self.benchmarker_agents[session_id] = BenchmarkerAgent()
            return self.benchmarker_agents.get(session_id, BenchmarkerAgent())
        return self.planner
    
    def _extract_number(self, message: str) -> Optional[int]:
        """메시지에서 숫자 추출 (1, 1번, 첫번째 등)"""
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
        confirmations = ['확정', '좋아', '이걸로', '다음', 'ok', 'OK', '완료']
        return any(c in message for c in confirmations)
    
    def _is_selection(self, message: str) -> bool:
        return self._extract_number(message) is not None
    
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
        
        # 숫자 선택 처리 (1, 2, 3... 또는 1번, 2번...)
        # 벤치마킹 단계에서는 숫자 선택 패스 (URL이 포함될 수 있음)
        if current_step != WorkflowStep.BENCHMARKING:
            num = self._extract_number(message)
            if num is not None:
                result = await self._handle_selection(session, num)
                self._save(session)
                return self._format_response(session, result)
        
        # 확정 처리
        if self._is_confirmation(message):
            result = await self._handle_next_step(session)
            self._save(session)
            return self._format_response(session, result)
        
        # 피드백 처리
        agent = self._get_current_agent(current_step, session_id)
        result = await agent.handle_feedback(message, images)
        
        # 벤치마킹 완료 시 컨텍스트 저장 및 리포트 표시
        if current_step == WorkflowStep.BENCHMARKING:
            if result.data:
                # 스킵인 경우 바로 다음 단계로
                if result.data.get('skipped'):
                    session.current_step = WorkflowStep.CHARACTER
                    char_result = await self.character_agent.execute({
                        'step': 'character',
                        **session.context
                    })
                    self._save(session)
                    return self._format_response(session, char_result)
                
                # 리포트 완료시 - 먼저 리포트를 보여주고 다음 단계 안내
                if result.data.get('report') and not result.needs_feedback:
                    session.context['benchmark_report'] = result.data['report']
                    session.context['benchmark_shown'] = True
                    # 리포트에 다음 단계 안내 추가
                    result.message = result.message + "\n\n---\n\n**리포트 확인 완료\!**\n다음 단계로 진행하려면 확인 또는 다음을 입력하세요."
                    result.needs_feedback = True
                    self._save(session)
                    return self._format_response(session, result)
                
                # 리포트를 이미 봤고 확인하면 다음 단계로
                if session.context.get('benchmark_shown'):
                    session.current_step = WorkflowStep.CHARACTER
                    char_result = await self.character_agent.execute({
                        'step': 'character',
                        **session.context
                    })
                    self._save(session)
                    return self._format_response(session, char_result)
        
        self._save(session)
        return self._format_response(session, result)
    
    async def _handle_selection(self, session: Session, num: int) -> AgentResult:
        """번호 선택 후 저장 및 다음 단계"""
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
        """다음 단계로 진행"""
        current_step = session.current_step
        next_idx = self.STEP_ORDER.index(current_step) + 1
        
        if next_idx >= len(self.STEP_ORDER):
            return self._complete_result(session)
        
        session.current_step = self.STEP_ORDER[next_idx]
        
        if session.current_step == WorkflowStep.COMPLETED:
            return self._complete_result(session)
        
        agent = self._get_current_agent(session.current_step, session.id)
        result = await agent.execute({
            'step': session.current_step.value,
            **session.context
        })
        
        # context 업데이트
        if result.data:
            if 'ideas' in result.data:
                session.context['video_ideas'] = result.data['ideas']
            if 'script' in result.data:
                session.context['script'] = result.data['script']
            if 'report' in result.data:
                session.context['benchmark_report'] = result.data['report']
        
        return result
    
    async def _handle_skip(self, session: Session) -> AgentResult:
        return await self._handle_next_step(session)
    
    def _complete_result(self, session: Session) -> AgentResult:
        channel = session.context.get('selected_channel_name', '')
        idea = session.context.get('selected_video_idea', {})
        idea_title = idea.get('title', '') if isinstance(idea, dict) else str(idea)
        has_benchmark = 'benchmark_report' in session.context
        
        msg = f'모든 기획 단계가 완료되었습니다!\n\n**채널명**: {channel}\n**영상 주제**: {idea_title}'
        if has_benchmark:
            msg += '\n**벤치마킹**: 완료'
        
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
