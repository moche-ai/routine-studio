import os
import httpx
from typing import List, Dict, Optional
from .base import BaseProvider


class LocalVLLMProvider(BaseProvider):
    name = "local_vllm"
    priority = 99
    is_local = True

    def __init__(self):
        self.base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8017/v1")
        self.model = os.getenv("VLLM_MODEL", "gpt-oss-120b")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None
    ) -> str:
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": full_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def is_available(self) -> bool:
        return True
