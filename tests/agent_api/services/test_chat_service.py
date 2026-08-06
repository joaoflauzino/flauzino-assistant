import uuid
from unittest.mock import AsyncMock
import pytest
from httpx import AsyncClient

from agent_api.services.chat import ChatService
from agent_api.schemas.assistant import AssistantResponse
from agent_api.models.chat import ChatSession, ChatMessage


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
    assert response.suggested_options == ["mercado", "comer_fora", "Todas as categorias"]
