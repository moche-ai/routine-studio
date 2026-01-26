from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_FEEDBACK = "waiting_feedback"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class AgentMessage:
    role: str
    content: str
    images: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass  
class AgentResult:
    success: bool
    data: Any = None
    message: str = ""
    images: List[str] = field(default_factory=list)
    needs_feedback: bool = False
    step: str = ""

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.status = AgentStatus.IDLE
        self.context: Dict[str, Any] = {}
        self.history: List[AgentMessage] = []
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        pass
    
    @abstractmethod
    async def handle_feedback(self, feedback: str, images: List[str] = None) -> AgentResult:
        pass
    
    def add_message(self, role: str, content: str, images: List[str] = None):
        self.history.append(AgentMessage(role=role, content=content, images=images or []))
    
    def set_context(self, key: str, value: Any):
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        return self.context.get(key, default)
