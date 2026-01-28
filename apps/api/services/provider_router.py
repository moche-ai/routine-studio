import logging
from typing import List, Dict, Optional, Type
from .quota_manager import quota_manager
from .providers import (
    BaseProvider,
    GroqProvider,
    OpenRouterProvider,
    GeminiLLMProvider,
    LocalVLLMProvider,
)

logger = logging.getLogger(__name__)


class ProviderRouter:
    def __init__(self):
        self.providers: List[BaseProvider] = []
        self._init_providers()

    def _init_providers(self):
        provider_classes: List[Type[BaseProvider]] = [
            GroqProvider,
            OpenRouterProvider,
            GeminiLLMProvider,
            LocalVLLMProvider,
        ]

        for cls in provider_classes:
            try:
                provider = cls()
                if provider.is_available():
                    self.providers.append(provider)
                    logger.info(f"[Router] {provider.name} enabled (priority={provider.priority})")
                else:
                    logger.warning(f"[Router] {provider.name} not available (missing API key)")
            except Exception as e:
                logger.error(f"[Router] Failed to init {cls.__name__}: {e}")

        self.providers.sort(key=lambda p: p.priority)
        logger.info(f"[Router] Active providers: {[p.name for p in self.providers]}")

    def _select_provider(self) -> Optional[BaseProvider]:
        for provider in self.providers:
            if provider.is_local:
                return provider

            if quota_manager.can_use(provider.name):
                return provider
            else:
                status = quota_manager.get_status(provider.name)
                logger.info(f"[Router] {provider.name} quota exhausted: {status}")

        return None

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None
    ) -> str:
        last_error = None

        for provider in self.providers:
            if not provider.is_local and not quota_manager.can_use(provider.name):
                logger.debug(f"[Router] Skipping {provider.name} (quota exhausted)")
                continue

            try:
                logger.info(f"[Router] Trying {provider.name}...")
                result = await provider.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    system_prompt=system_prompt
                )

                if not provider.is_local:
                    quota_manager.use(provider.name, 1)
                    status = quota_manager.get_status(provider.name)
                    logger.info(f"[Router] {provider.name} success. Remaining: {status['remaining']}/{status['limit']}")

                return result

            except Exception as e:
                last_error = e
                logger.warning(f"[Router] {provider.name} failed: {e}")
                continue

        if last_error:
            raise last_error
        raise RuntimeError("No providers available")

    async def generate(self, prompt: str, **kwargs) -> str:
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)

    def get_status(self) -> Dict:
        result = {
            "providers": [],
            "quotas": quota_manager.get_all_status()
        }
        for provider in self.providers:
            result["providers"].append({
                "name": provider.name,
                "priority": provider.priority,
                "is_local": provider.is_local,
                "available": provider.is_available(),
                "can_use": provider.is_local or quota_manager.can_use(provider.name)
            })
        return result


provider_router = ProviderRouter()
