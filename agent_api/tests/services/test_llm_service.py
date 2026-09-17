from unittest.mock import AsyncMock, MagicMock

from google.api_core.exceptions import GoogleAPIError
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
import pytest

from agent_api.core.exceptions import LLMParsingError, LLMProviderError, ServiceError
from agent_api.schemas.assistant import AssistantResponse
from agent_api.services.finance import FinanceService
from agent_api.services.graph import GraphService
from agent_api.services.llm import get_llm_response, get_system_prompt


@pytest.fixture
def mock_llm():
    return MagicMock(spec=BaseChatModel)


@pytest.fixture
def mock_finance_service():
    service = AsyncMock(spec=FinanceService)
    service.get_categories.return_value = ["mercado", "lazer"]
    service.get_payment_methods.return_value = ["pix", "cartao_credito"]
    return service


@pytest.fixture
def mock_graph_service():
    return AsyncMock(spec=GraphService)


@pytest.mark.asyncio
async def test_get_llm_response_success(mocker, mock_finance_service, mock_graph_service, mock_llm):
    """Test that get_llm_response runs agent and returns structured response."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={
            "messages": [HumanMessage(content="Olá"), AIMessage(content="Olá!")],
            "structured_response": AssistantResponse(
                response_message="Dados recebidos com sucesso!",
                suggested_options=["Sim", "Não"],
                is_complete=True,
            ),
        }
    )
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    sample_history = [
        {"role": "user", "content": "Olá"},
        {"role": "assistant", "content": "Olá, como posso ajudar?"},
    ]

    result = await get_llm_response(
        sample_history,
        finance_service=mock_finance_service,
        graph_service=mock_graph_service,
        llm=mock_llm,
    )

    assert result.response_message == "Dados recebidos com sucesso!"
    assert result.suggested_options == ["Sim", "Não"]
    assert result.is_complete is True
    mock_agent.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_llm_response_with_image(
    mocker, mock_finance_service, mock_graph_service, mock_llm
):
    """Test that get_llm_response attaches image_base64 from agent state to structured response."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={
            "messages": [HumanMessage(content="gere um gráfico")],
            "structured_response": AssistantResponse(
                response_message="Aqui está o gráfico!",
                is_complete=False,
            ),
            "image_base64": "base64_chart_bytes",
        }
    )
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    sample_history = [{"role": "user", "content": "gere um gráfico"}]

    result = await get_llm_response(
        sample_history,
        finance_service=mock_finance_service,
        graph_service=mock_graph_service,
        llm=mock_llm,
    )

    assert result.response_message == "Aqui está o gráfico!"
    assert result.image_base64 == "base64_chart_bytes"


@pytest.mark.asyncio
async def test_get_llm_response_plain_text_fallback(
    mocker, mock_finance_service, mock_graph_service, mock_llm
):
    """Test fallback when agent does not produce structured_response but has text in last message."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Oi"),
                AIMessage(content="Resposta em texto simples sem structured output."),
            ],
            "structured_response": None,
        }
    )
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    sample_history = [{"role": "user", "content": "Oi"}]

    result = await get_llm_response(
        sample_history,
        finance_service=mock_finance_service,
        graph_service=mock_graph_service,
        llm=mock_llm,
    )

    assert result.response_message == "Resposta em texto simples sem structured output."
    assert result.is_complete is False


@pytest.mark.asyncio
async def test_get_llm_response_parsing_error(
    mocker, mock_finance_service, mock_graph_service, mock_llm
):
    """Test that OutputParserException is caught and raised as LLMParsingError."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(side_effect=OutputParserException("Parsing failed"))
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    with pytest.raises(LLMParsingError) as exc_info:
        await get_llm_response(
            [{"role": "user", "content": "test"}],
            finance_service=mock_finance_service,
            graph_service=mock_graph_service,
            llm=mock_llm,
        )

    assert "Failed to parse LLM response" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_llm_response_google_api_error(
    mocker, mock_finance_service, mock_graph_service, mock_llm
):
    """Test that GoogleAPIError is caught and raised as LLMProviderError."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(side_effect=GoogleAPIError("API Error"))
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    with pytest.raises(LLMProviderError) as exc_info:
        await get_llm_response(
            [{"role": "user", "content": "test"}],
            finance_service=mock_finance_service,
            graph_service=mock_graph_service,
            llm=mock_llm,
        )

    assert "Google Gemini Error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_llm_response_unknown_error(
    mocker, mock_finance_service, mock_graph_service, mock_llm
):
    """Test that generic Exception is caught and raised as ServiceError."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(side_effect=Exception("Unexpected boom"))
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    with pytest.raises(ServiceError) as exc_info:
        await get_llm_response(
            [{"role": "user", "content": "test"}],
            finance_service=mock_finance_service,
            graph_service=mock_graph_service,
            llm=mock_llm,
        )

    assert "Unexpected LLM Error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_system_prompt_includes_categories(mock_finance_service):
    """Test that get_system_prompt queries finance_service for categories and payment methods."""
    prompt = await get_system_prompt(finance_service=mock_finance_service)

    assert "'mercado'" in prompt
    assert "'lazer'" in prompt
    assert "'pix'" in prompt
    assert "'cartao_credito'" in prompt
    mock_finance_service.get_categories.assert_awaited_once()
    mock_finance_service.get_payment_methods.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_system_prompt_fallback_on_error():
    """Test fallback to empty strings when finance_service fails."""
    broken_service = AsyncMock(spec=FinanceService)
    broken_service.get_categories.side_effect = Exception("API down")
    broken_service.get_payment_methods.side_effect = Exception("API down")

    prompt = await get_system_prompt(finance_service=broken_service)

    assert "CATEGORIAS VÁLIDAS" in prompt
    assert "[]" in prompt


@pytest.mark.asyncio
async def test_get_system_prompt_platform_telegram(mock_finance_service):
    """Test that platform='telegram' includes telegram formatting instructions."""
    prompt = await get_system_prompt(finance_service=mock_finance_service, platform="telegram")

    assert "Formatação para Telegram" in prompt
