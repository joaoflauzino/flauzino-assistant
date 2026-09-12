from unittest.mock import AsyncMock
import uuid

from httpx import AsyncClient
import pytest

from agent_api.models.chat import ChatMessage, ChatSession
from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.spending import SpendingDetails
from agent_api.services.chat import ChatService


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=AsyncClient)


@pytest.fixture
def chat_service(mock_db_session, mock_http_client):
    service = ChatService(mock_db_session, mock_http_client)
    # Mock Repository inside service
    service.repository = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_process_message_new_session(chat_service, mocker):
    # Arrange
    message = "Hello"
    fake_session_id = uuid.uuid4()

    mock_session = ChatSession(id=fake_session_id)
    chat_service.repository.create_session.return_value = mock_session
    chat_service.repository.get_messages.return_value = [ChatMessage(role="user", content="Hello")]

    # Mock LLM
    mock_get_llm = mocker.patch("agent_api.services.chat.get_llm_response", new_callable=AsyncMock)
    mock_get_llm.return_value = AssistantResponse(response_message="Hi there", is_complete=False)

    # Act
    response = await chat_service.process_message(message, None)

    # Assert
    assert response.session_id == str(fake_session_id)
    assert response.response == "Hi there"
    assert len(response.history) == 2  # User + Assistant

    chat_service.repository.create_session.assert_awaited_once()
    chat_service.repository.add_message.assert_any_await(fake_session_id, "user", "Hello")
    chat_service.repository.add_message.assert_any_await(fake_session_id, "assistant", "Hi there")


@pytest.mark.asyncio
async def test_process_message_existing_session_not_found(chat_service, mocker):
    # Arrange
    fake_id = str(uuid.uuid4())
    chat_service.repository.get_session.return_value = None

    new_session_id = uuid.uuid4()
    mock_session = ChatSession(id=new_session_id)
    chat_service.repository.create_session.return_value = mock_session
    chat_service.repository.get_messages.return_value = [ChatMessage(role="user", content="Hi")]

    # Mock LLM
    mock_get_llm = mocker.patch("agent_api.services.chat.get_llm_response", new_callable=AsyncMock)
    mock_get_llm.return_value = AssistantResponse(response_message="Hi there", is_complete=False)

    # Act
    response = await chat_service.process_message("Hi", fake_id)

    # Assert
    assert response.session_id == str(new_session_id)
    assert response.response == "Hi there"
    chat_service.repository.create_session.assert_awaited_once()
    chat_service.repository.add_message.assert_any_await(new_session_id, "user", "Hi")


@pytest.mark.asyncio
async def test_process_message_suggested_options(chat_service, mocker):
    # Arrange
    message = "saldo"
    fake_session_id = uuid.uuid4()

    mock_session = ChatSession(id=fake_session_id)
    chat_service.repository.create_session.return_value = mock_session
    chat_service.repository.get_messages.return_value = [ChatMessage(role="user", content="saldo")]

    # Mock LLM
    mock_get_llm = mocker.patch("agent_api.services.chat.get_llm_response", new_callable=AsyncMock)
    mock_get_llm.return_value = AssistantResponse(
        response_message="Qual categoria?",
        is_complete=False,
        suggested_options=["mercado", "comer_fora", "Todas as categorias"],
    )

    # Act
    response = await chat_service.process_message(message, None)

    # Assert
    assert response.response == "Qual categoria?"
    assert response.suggested_options == [
        "mercado",
        "comer_fora",
        "Todas as categorias",
    ]


@pytest.mark.asyncio
async def test_process_message_graph_generation(chat_service, mocker):
    # Arrange
    message = "gere um gráfico de pizza"
    fake_session_id = uuid.uuid4()

    mock_session = ChatSession(id=fake_session_id)
    chat_service.repository.create_session.return_value = mock_session
    chat_service.repository.get_messages.return_value = [ChatMessage(role="user", content=message)]

    # Mock LLM
    mock_get_llm = mocker.patch("agent_api.services.chat.get_llm_response", new_callable=AsyncMock)
    mock_get_llm.return_value = AssistantResponse(
        response_message="Gerando gráfico",
        is_complete=False,
        requested_graph_type="pie",
        requested_graph_categories=["mercado"],
    )

    # Mock HTTP response for balance fetch
    mock_balance_response = mocker.MagicMock()
    mock_balance_response.status_code = 200
    mock_balance_response.json.return_value = [
        {
            "category_display_name": "Mercado",
            "limit": 1000.0,
            "spent": 300.0,
            "available": 700.0,
        }
    ]
    chat_service.http_client.get.return_value = mock_balance_response

    # Mock GraphService
    mocker.patch.object(
        chat_service.graph_service,
        "generate_chart",
        new_callable=AsyncMock,
        return_value="base64_graph_image",
    )

    # Act
    response = await chat_service.process_message(message, None)

    # Assert
    assert response.image_base64 == "base64_graph_image"
    assert response.response == "Aqui está o gráfico que você pediu!"


@pytest.mark.asyncio
async def test_process_message_executes_finance_action(chat_service, mocker):
    # Arrange
    message = "Sim, confirma"
    fake_session_id = uuid.uuid4()

    mock_session = ChatSession(id=fake_session_id)
    chat_service.repository.create_session.return_value = mock_session
    chat_service.repository.get_messages.return_value = [ChatMessage(role="user", content=message)]

    llm_resp = AssistantResponse(
        response_message="Gasto registrado!",
        is_complete=True,
        is_confirmed=True,
        spending_details=SpendingDetails(
            categoria="mercado",
            valor=50.0,
            metodo_pagamento="pix",
            item_comprado="Frutas",
            local_compra="Quitanda",
        ),
    )
    mocker.patch(
        "agent_api.services.chat.get_llm_response",
        new_callable=AsyncMock,
        return_value=llm_resp,
    )

    mock_register = mocker.patch.object(
        chat_service.finance_service,
        "register",
        new_callable=AsyncMock,
        return_value={"id": 123},
    )

    # Act
    response = await chat_service.process_message(message, None)

    # Assert
    assert response.is_complete is True
    mock_register.assert_awaited_once_with(llm_resp)
