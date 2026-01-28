import os
import httpx
from typing import List, Dict, Optional
from .base import BaseProvider


class OpenRouterProvider(BaseProvider):
    name = "openrouter"
    priority = 2
    is_local = False

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", os.getenv("OPEN_ROUTER_API_KEY", ""))
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "meta-llama/llama-3.3-70b-instruct:free"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None
    ) -> str:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://routine-studio.app",
                    "X-Title": "Routine Studio"
                },
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
        return bool(self.api_key)
