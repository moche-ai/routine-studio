import os
import httpx
from typing import List, Dict, Any, Optional

USE_PROVIDER_ROUTER = os.getenv("USE_PROVIDER_ROUTER", "true").lower() == "true"


class LLMService:
    def __init__(self, base_url: str = "http://localhost:8017/v1"):
        self.base_url = base_url
        self.model = "gpt-oss-120b"
        self._router = None

    def _get_router(self):
        if self._router is None:
            from .provider_router import provider_router
            self._router = provider_router
        return self._router

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None
    ) -> str:
        if USE_PROVIDER_ROUTER:
            router = self._get_router()
            return await router.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            )

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

    async def generate(self, prompt: str, **kwargs) -> str:
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)

    def get_status(self) -> Dict:
        if USE_PROVIDER_ROUTER:
            return self._get_router().get_status()
        return {"mode": "direct", "base_url": self.base_url, "model": self.model}


llm_service = LLMService()
