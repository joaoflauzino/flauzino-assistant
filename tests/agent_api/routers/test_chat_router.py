from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from agent_api.main import app
from agent_api.schemas.dtos import ChatResponse, ChatMessage
from finance_api.schemas.enums import CategoryEnum

# Mark all tests as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_client():
    """Fixture for a test client for the FastAPI app."""
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client


@pytest.fixture
def mock_chat_service(mocker):
    """Fixture to mock ChatService."""
    # Patch the class so the router gets our mock instance
    MockService = mocker.patch("agent_api.routers.chat.ChatService")
    instance = MockService.return_value
    instance.process_message = AsyncMock()
    return instance


async def test_chat_endpoint_delegates_to_service(test_client, mock_chat_service):
    """
    Test that the chat endpoint correctly delegates to ChatService.process_message.
    """
    # Arrange
    payload = {"message": "Hello"}
    fake_session_id = str(uuid.uuid4())

    # Mock Service Response
    mock_chat_service.process_message.return_value = ChatResponse(
        response="Hi",
        session_id=fake_session_id,
        history=[
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi"),
        ],
    )

    # Act
    response = await test_client.post("/chat", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Hi"
    assert data["session_id"] == fake_session_id

    # Verify service call
    mock_chat_service.process_message.assert_awaited_once_with("Hello", None)


async def test_chat_endpoint_passes_session_id(test_client, mock_chat_service):
    """
    Test that the chat endpoint passes the session_id to the service.
    """
    # Arrange
    fake_id = str(uuid.uuid4())
    payload = {"message": "Hello again", "session_id": fake_id}

    mock_chat_service.process_message.return_value = ChatResponse(
        response="Hi again", session_id=fake_id, history=[]
    )

    # Act
    await test_client.post("/chat", json=payload)

    # Assert
    mock_chat_service.process_message.assert_awaited_once_with("Hello again", fake_id)
