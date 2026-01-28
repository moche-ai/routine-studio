from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseProvider(ABC):
    name: str = "base"
    priority: int = 99
    is_local: bool = False

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None
    ) -> str:
        pass

    async def generate(self, prompt: str, **kwargs) -> str:
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)

    @abstractmethod
    def is_available(self) -> bool:
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} priority={self.priority}>"
