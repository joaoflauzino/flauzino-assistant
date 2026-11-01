from collections.abc import Callable
from enum import StrEnum
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from agent_api.core.exceptions import LLMProviderError
from agent_api.settings import settings


class LLMProfile(StrEnum):
    CHAT_AGENT = "chat_agent"
    BATCH_CLASSIFIER = "batch_classifier"


type LLMCreator = Callable[[], BaseChatModel]


class LLMFactory:
    def __init__(self) -> None:
        self._registry: dict[LLMProfile, LLMCreator] = {}

    def register(self, profile: LLMProfile, creator: LLMCreator) -> None:
        self._registry[profile] = creator

    def create(self, profile: LLMProfile = LLMProfile.CHAT_AGENT) -> BaseChatModel:
        creator = self._registry.get(profile)
        if creator is None:
            supported = ", ".join(self._registry.keys())
            raise LLMProviderError(
                f"Perfil de LLM '{profile}' não registrado. Suportados: [{supported}]"
            )
        return creator()


def _build_openai_chat_agent() -> BaseChatModel:
    api_key = settings.OPENAI_API_KEY
    if not api_key or not api_key.strip():
        raise LLMProviderError(
            "OPENAI_API_KEY não foi configurada ou está vazia no ambiente (.env). "
            "Por favor, configure sua chave OPENAI_API_KEY."
        )
    return ChatOpenAI(
        model=settings.MODEL_NAME,
        api_key=api_key,
        max_retries=2,
        reasoning_effort="none",
    )


def _build_openai_batch_classifier() -> BaseChatModel:
    api_key = settings.OPENAI_API_KEY
    if not api_key or not api_key.strip():
        raise LLMProviderError(
            "OPENAI_API_KEY não foi configurada ou está vazia no ambiente (.env). "
            "Por favor, configure sua chave OPENAI_API_KEY."
        )
    return ChatOpenAI(
        model=settings.MODEL_NAME,
        api_key=api_key,
        max_retries=2,
        reasoning_effort="none",
    )


def build_default_llm_factory() -> LLMFactory:
    factory = LLMFactory()
    factory.register(LLMProfile.CHAT_AGENT, _build_openai_chat_agent)
    factory.register(LLMProfile.BATCH_CLASSIFIER, _build_openai_batch_classifier)
    return factory


@lru_cache
def get_llm(profile: LLMProfile = LLMProfile.CHAT_AGENT) -> BaseChatModel:
    """Cached singleton instance of BaseChatModel resolved via LLMFactory."""
    factory = build_default_llm_factory()
    return factory.create(profile)
