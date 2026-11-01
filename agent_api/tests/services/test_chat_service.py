import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent_api.dependencies import (
    get_agent_service,
    get_chat_repository,
    get_chat_service,
    get_classify_service,
)
from agent_api.models.chat import ChatMessage, ChatSession
from agent_api.repositories.chat_repository import ChatRepositoryProtocol
from agent_api.schemas.assistant import AssistantResponse
from agent_api.services.agent import AgentService
from agent_api.services.chat import ChatService


@pytest.fixture
def mock_repo():
    return AsyncMock(spec=ChatRepositoryProtocol)


@pytest.fixture
def mock_agent_service():
    return AsyncMock(spec=AgentService)


@pytest.fixture
def chat_service(mock_repo, mock_agent_service):
    return ChatService(mock_repo, mock_agent_service)


@pytest.mark.asyncio
async def test_chat_service_accepts_legacy_async_session(mock_agent_service):
    mock_session = AsyncMock(spec=AsyncSession)
    service = ChatService(mock_session, mock_agent_service)
    assert hasattr(service.repository, "create_session")


def test_agent_dependencies_wiring():
    mock_db = MagicMock(spec=AsyncSession)
    mock_http = MagicMock()
    mock_llm = MagicMock()

    repo = get_chat_repository(mock_db)
    agent_svc = get_agent_service(mock_http, mock_llm)
    chat_svc = get_chat_service(repo, agent_svc)
    clf_svc = get_classify_service(mock_llm)

    assert chat_svc.repository is repo
    assert chat_svc.agent_service is agent_svc
    assert clf_svc is not None


@pytest.mark.asyncio
async def test_process_message_new_session(chat_service):
    # Arrange
    message = "Hello"
    fake_session_id = uuid.uuid4()

    mock_session = ChatSession(id=fake_session_id)
    chat_service.repository.create_session.return_value = mock_session
    chat_service.repository.get_messages.return_value = [ChatMessage(role="user", content="Hello")]
    chat_service.agent_service.get_response.return_value = AssistantResponse(
        response_message="Hi there", is_complete=False
    )

    # Act
    response = await chat_service.process_message(message, None)

    # Assert
    assert response.session_id == str(fake_session_id)
    assert response.response == "Hi there"
    assert len(response.history) == 2  # User + Assistant

    chat_service.repository.create_session.assert_awaited_once()
    chat_service.repository.add_message.assert_any_await(fake_session_id, "user", "Hello")
    chat_service.repository.add_message.assert_any_await(fake_session_id, "assistant", "Hi there")
    chat_service.agent_service.get_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_message_existing_session_found_and_invalid_uuid(chat_service):
    valid_id = uuid.uuid4()
    chat_service.repository.get_session.return_value = ChatSession(id=valid_id)
    chat_service.repository.get_messages.return_value = [ChatMessage(role="user", content="Oi")]
    chat_service.agent_service.get_response.return_value = AssistantResponse(
        response_message="Olá", is_complete=False
    )

    res_existing = await chat_service.process_message("Oi", str(valid_id))
    assert res_existing.session_id == str(valid_id)

    # Invalid UUID string falls back to create_session
    new_id = uuid.uuid4()
    chat_service.repository.create_session.return_value = ChatSession(id=new_id)
    res_invalid = await chat_service.process_message("Oi", "not-a-valid-uuid")
    assert res_invalid.session_id == str(new_id)


@pytest.mark.asyncio
async def test_process_message_existing_session_not_found(chat_service):
    # Arrange
    fake_id = str(uuid.uuid4())
    chat_service.repository.get_session.return_value = None

    new_session_id = uuid.uuid4()
    mock_session = ChatSession(id=new_session_id)
    chat_service.repository.create_session.return_value = mock_session
    chat_service.repository.get_messages.return_value = [ChatMessage(role="user", content="Hi")]
    chat_service.agent_service.get_response.return_value = AssistantResponse(
        response_message="Hi there", is_complete=False
    )

    # Act
    response = await chat_service.process_message("Hi", fake_id)

    # Assert
    assert response.session_id == str(new_session_id)
    assert response.response == "Hi there"
    chat_service.repository.create_session.assert_awaited_once()
    chat_service.repository.add_message.assert_any_await(new_session_id, "user", "Hi")


@pytest.mark.asyncio
async def test_process_message_suggested_options(chat_service):
    # Arrange
    message = "saldo"
    fake_session_id = uuid.uuid4()

    mock_session = ChatSession(id=fake_session_id)
    chat_service.repository.create_session.return_value = mock_session
    chat_service.repository.get_messages.return_value = [ChatMessage(role="user", content="saldo")]
    chat_service.agent_service.get_response.return_value = AssistantResponse(
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
async def test_process_message_graph_generation(chat_service):
    # Arrange
    message = "gere um gráfico de pizza"
    fake_session_id = uuid.uuid4()

    mock_session = ChatSession(id=fake_session_id)
    chat_service.repository.create_session.return_value = mock_session
    chat_service.repository.get_messages.return_value = [ChatMessage(role="user", content=message)]
    chat_service.agent_service.get_response.return_value = AssistantResponse(
        response_message="Aqui está o gráfico que você pediu!",
        is_complete=False,
        image_base64="base64_graph_image",
    )

    # Act
    response = await chat_service.process_message(message, None)

    # Assert
    assert response.image_base64 == "base64_graph_image"
    assert response.response == "Aqui está o gráfico que você pediu!"


@pytest.mark.asyncio
async def test_process_message_delegates_to_agent_service(chat_service):
    # Arrange
    message = "Sim, confirma"
    fake_session_id = uuid.uuid4()

    mock_session = ChatSession(id=fake_session_id)
    chat_service.repository.create_session.return_value = mock_session
    chat_service.repository.get_messages.return_value = [ChatMessage(role="user", content=message)]

    llm_resp = AssistantResponse(
        response_message="Gasto registrado!",
        is_complete=True,
    )
    chat_service.agent_service.get_response.return_value = llm_resp

    # Act
    response = await chat_service.process_message(message, None, platform="telegram")

    # Assert
    assert response.is_complete is True
    assert response.response == "Gasto registrado!"
    chat_service.agent_service.get_response.assert_awaited_once_with(
        [{"role": "user", "content": message}],
        platform="telegram",
    )
