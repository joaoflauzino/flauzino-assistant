from unittest.mock import AsyncMock, MagicMock

import pytest
from groq import GroqError
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from openai import OpenAIError

from agent_api.core.exceptions import LLMParsingError, LLMProviderError, ServiceError
from agent_api.schemas.assistant import AssistantResponse
from agent_api.services.agent import AgentService
from agent_api.services.finance import FinanceService
from agent_api.services.graph import GraphService


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


@pytest.fixture
def agent_service(mock_llm, mock_finance_service, mock_graph_service):
    return AgentService(
        llm=mock_llm,
        finance_service=mock_finance_service,
        graph_service=mock_graph_service,
    )


@pytest.mark.asyncio
async def test_agent_service_get_response_success(mocker, agent_service):
    """Test that AgentService.get_response runs agent and extracts structured_response."""
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

    result = await agent_service.get_response(sample_history)

    assert result.response_message == "Dados recebidos com sucesso!"
    assert result.suggested_options == ["Sim", "Não"]
    assert result.is_complete is True
    mock_agent.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_service_get_response_with_image(mocker, agent_service):
    """Test that AgentService.get_response attaches image_base64 from agent state."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={
            "messages": [HumanMessage(content="gere um gráfico")],
            "structured_response": AssistantResponse(
                response_message="Aqui está o gráfico!",
                suggested_options=[],
                is_complete=True,
            ),
            "image_base64": "base64_chart_bytes",
        }
    )
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    sample_history = [{"role": "user", "content": "gere um gráfico"}]

    result = await agent_service.get_response(sample_history)

    assert result.response_message == "Aqui está o gráfico!"
    assert result.image_base64 == "base64_chart_bytes"
    assert result.is_complete is True


@pytest.mark.asyncio
async def test_agent_service_get_response_dict_structured_response(mocker, agent_service):
    """Test that AgentService handles dict structured_response properly."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={
            "messages": [HumanMessage(content="olá")],
            "structured_response": {
                "response_message": "Resposta em formato dict",
                "suggested_options": ["Opção 1"],
                "is_complete": False,
            },
        }
    )
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    result = await agent_service.get_response([{"role": "user", "content": "olá"}])

    assert result.response_message == "Resposta em formato dict"
    assert result.suggested_options == ["Opção 1"]
    assert result.is_complete is False


@pytest.mark.asyncio
async def test_agent_service_get_response_plain_text_fallback(mocker, agent_service):
    """Test fallback when agent does not output structured response but has text in last message."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Oi"),
                AIMessage(content="Resposta em texto simples fallback."),
            ],
            "structured_response": None,
        }
    )
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    sample_history = [{"role": "user", "content": "Oi"}]

    result = await agent_service.get_response(sample_history)

    assert result.response_message == "Resposta em texto simples fallback."
    assert result.is_complete is False


@pytest.mark.asyncio
async def test_agent_service_get_response_parsing_error(mocker, agent_service):
    """Test that OutputParserException is caught and raised as LLMParsingError."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(side_effect=OutputParserException("Parsing failed"))
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    with pytest.raises(LLMParsingError) as exc_info:
        await agent_service.get_response([{"role": "user", "content": "test"}])

    assert "Failed to parse LLM response" in str(exc_info.value)


@pytest.mark.asyncio
async def test_agent_service_get_response_groq_error(mocker, agent_service):
    """Test that GroqError is caught and raised as LLMProviderError."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(side_effect=GroqError("API Error"))
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    with pytest.raises(LLMProviderError) as exc_info:
        await agent_service.get_response([{"role": "user", "content": "test"}])

    assert "Groq API Error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_agent_service_get_response_openai_error(mocker, agent_service):
    """Test that OpenAIError is caught and raised as LLMProviderError."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(side_effect=OpenAIError("API Error"))
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    with pytest.raises(LLMProviderError) as exc_info:
        await agent_service.get_response([{"role": "user", "content": "test"}])

    assert "OpenAI API Error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_agent_service_get_response_unknown_error(mocker, agent_service):
    """Test that generic Exception is caught and raised as ServiceError."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(side_effect=Exception("Unexpected boom"))
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    with pytest.raises(ServiceError) as exc_info:
        await agent_service.get_response([{"role": "user", "content": "test"}])

    assert "Unexpected LLM Error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_agent_service_extracts_response_from_tool_calls(mocker, agent_service):
    """Test resilience path: AssistantResponse arrives as a tool call inside messages."""
    tool_call_message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "AssistantResponse",
                "args": {
                    "response_message": "Resposta via tool call",
                    "suggested_options": ["Ok"],
                    "is_complete": True,
                },
                "id": "call_1",
            }
        ],
    )
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={
            "messages": [HumanMessage(content="oi"), tool_call_message],
            "structured_response": None,
            "image_base64": "chart_base64",
        }
    )
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    result = await agent_service.get_response([{"role": "user", "content": "oi"}])

    assert result.response_message == "Resposta via tool call"
    assert result.suggested_options == ["Ok"]
    assert result.is_complete is True
    assert result.image_base64 == "chart_base64"


@pytest.mark.asyncio
async def test_agent_service_ignores_unrelated_tool_calls(mocker, agent_service):
    """Test that tool calls other than AssistantResponse fall back to plain text."""
    tool_call_message = AIMessage(
        content="Texto final do agente",
        tool_calls=[{"name": "gerar_grafico", "args": {"periodo": "2026-10"}, "id": "call_graph"}],
    )
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={
            "messages": [HumanMessage(content="gere um gráfico"), tool_call_message],
            "structured_response": None,
        }
    )
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    result = await agent_service.get_response([{"role": "user", "content": "gráfico"}])

    assert result.response_message == "Texto final do agente"
    assert result.is_complete is False


@pytest.mark.asyncio
async def test_agent_service_fallback_without_messages_uses_default_text(mocker, agent_service):
    """Test fallback default message when the agent returns no messages at all."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"messages": [], "structured_response": None})
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    result = await agent_service.get_response([{"role": "user", "content": "oi"}])

    assert result.response_message == "Desculpe, não consegui processar a resposta adequadamente."
    assert result.is_complete is False
    assert result.suggested_options == ["Sim", "Não"]


@pytest.mark.asyncio
async def test_agent_service_dict_response_does_not_override_own_image(mocker, agent_service):
    """Test that a structured dict keeps its own image instead of the state fallback."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={
            "messages": [HumanMessage(content="gere um gráfico")],
            "structured_response": {
                "response_message": "Gráfico gerado",
                "suggested_options": [],
                "is_complete": True,
                "image_base64": "image_from_dict",
            },
            "image_base64": "image_from_state",
        }
    )
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    result = await agent_service.get_response([{"role": "user", "content": "gráfico"}])

    assert result.image_base64 == "image_from_dict"


@pytest.mark.asyncio
async def test_agent_service_text_fallback_keeps_state_image(mocker, agent_service):
    """Test that the plain-text fallback propagates the image stored in the state."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(
        return_value={
            "messages": [HumanMessage(content="oi"), AIMessage(content="Segue o gráfico")],
            "structured_response": None,
            "image_base64": "image_from_state",
        }
    )
    mocker.patch("agent_api.services.agent.create_agent", return_value=mock_agent)

    result = await agent_service.get_response([{"role": "user", "content": "oi"}])

    assert result.response_message == "Segue o gráfico"
    assert result.image_base64 == "image_from_state"


@pytest.mark.asyncio
async def test_get_system_prompt_includes_categories(agent_service, mock_finance_service):
    """Test that get_system_prompt queries finance_service for categories and payment methods."""
    prompt = await agent_service.get_system_prompt()

    assert "'mercado'" in prompt
    assert "'lazer'" in prompt
    assert "'pix'" in prompt
    assert "'cartao_credito'" in prompt
    mock_finance_service.get_categories.assert_awaited_once()
    mock_finance_service.get_payment_methods.assert_awaited_once()
