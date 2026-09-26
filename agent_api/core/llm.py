from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from agent_api.settings import settings


@lru_cache
def get_llm() -> BaseChatModel:
    """Singleton cached instance of ChatOpenAI."""
    api_key = settings.OPENAI_API_KEY
    model = settings.MODEL_NAME
    return ChatOpenAI(model=model, api_key=api_key, max_retries=2, reasoning_effort="none")
