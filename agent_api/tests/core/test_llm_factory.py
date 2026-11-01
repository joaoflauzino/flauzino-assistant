from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models.chat_models import BaseChatModel

from agent_api.core.exceptions import LLMProviderError
from agent_api.core.llm import (
    LLMFactory,
    LLMProfile,
    build_default_llm_factory,
    build_openai_batch_classifier,
    build_openai_chat_agent,
    get_llm,
)


def test_llm_factory_register_and_create():
    factory = LLMFactory()
    mock_chat_model = MagicMock(spec=BaseChatModel)
    mock_batch_model = MagicMock(spec=BaseChatModel)

    factory.register(LLMProfile.CHAT_AGENT, lambda: mock_chat_model)
    factory.register(LLMProfile.BATCH_CLASSIFIER, lambda: mock_batch_model)

    assert factory.create(LLMProfile.CHAT_AGENT) is mock_chat_model
    assert factory.create(LLMProfile.BATCH_CLASSIFIER) is mock_batch_model


def test_llm_factory_unregistered_profile_raises_error():
    factory = LLMFactory()
    with pytest.raises(LLMProviderError) as exc:
        factory.create(LLMProfile.CHAT_AGENT)
    assert "Perfil de LLM 'chat_agent' não registrado" in str(exc.value)


def test_build_default_llm_factory_contains_profiles():
    factory = build_default_llm_factory()
    assert LLMProfile.CHAT_AGENT in factory._registry
    assert LLMProfile.BATCH_CLASSIFIER in factory._registry


@patch("agent_api.core.llm.settings")
def test_default_creators_raise_when_missing_api_key(mock_settings):
    mock_settings.OPENAI_API_KEY = ""
    mock_settings.MODEL_NAME = "gpt-4o-mini"

    with pytest.raises(LLMProviderError) as exc:
        build_openai_chat_agent()
    assert "OPENAI_API_KEY não foi configurada" in str(exc.value)

    with pytest.raises(LLMProviderError) as exc:
        build_openai_batch_classifier()
    assert "OPENAI_API_KEY não foi configurada" in str(exc.value)


@patch("agent_api.core.llm.ChatOpenAI")
@patch("agent_api.core.llm.settings")
def test_get_llm_cached(mock_settings, mock_chat_openai):
    mock_settings.OPENAI_API_KEY = "sk-fake-test-key"
    mock_settings.MODEL_NAME = "gpt-4o-mini"
    mock_instance = MagicMock(spec=BaseChatModel)
    mock_chat_openai.return_value = mock_instance

    get_llm.cache_clear()

    model1 = get_llm(LLMProfile.CHAT_AGENT)
    model2 = get_llm(LLMProfile.CHAT_AGENT)

    assert model1 is model2
    assert model1 is mock_instance
