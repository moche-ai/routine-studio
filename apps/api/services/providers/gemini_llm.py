import os
from typing import List, Dict, Optional
from .base import BaseProvider


class GeminiLLMProvider(BaseProvider):
    name = "gemini"
    priority = 3
    is_local = False

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-2.5-flash"
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None
    ) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")

        contents = []
        if system_prompt:
            contents.append(f"System: {system_prompt}\n\n")
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                contents.append(content)
            elif role == "assistant":
                contents.append(f"Assistant: {content}")

        client = self._get_client()
        response = client.models.generate_content(
            model=self.model,
            contents=contents,
            config={
                "temperature": temperature,
                "max_output_tokens": max_tokens
            }
        )
        return response.text

    def is_available(self) -> bool:
        return bool(self.api_key)
