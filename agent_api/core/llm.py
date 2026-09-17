from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from agent_api.settings import settings


@lru_cache
def get_llm() -> ChatGoogleGenerativeAI:
    """Singleton cached instance of ChatGoogleGenerativeAI."""
    kwargs = {
        "model": settings.MODEL_NAME,
        "temperature": 0,
    }
    if settings.GOOGLE_API_KEY:
        kwargs["api_key"] = settings.GOOGLE_API_KEY
    else:
        # Dummy key to allow instantiation in test/CI environments without error
        kwargs["api_key"] = "test-api-key"

    return ChatGoogleGenerativeAI(**kwargs)
