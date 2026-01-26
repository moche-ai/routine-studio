import httpx
from typing import List, Dict, Any, Optional

class LLMService:
    """gpt-oss-120b-longctx vLLM 서비스"""
    
    def __init__(self, base_url: str = "http://localhost:8017/v1"):
        self.base_url = base_url
        self.model = "gpt-oss-120b-longctx"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None
    ) -> str:
        """LLM 채팅 요청"""
        
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
        """단순 텍스트 생성"""
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)

# 싱글톤 인스턴스
llm_service = LLMService()
