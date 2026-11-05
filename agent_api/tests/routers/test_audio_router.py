from unittest.mock import AsyncMock

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from agent_api.dependencies import get_audio_service, get_chat_service
from agent_api.main import app
from agent_api.schemas.dtos import ChatResponse
from agent_api.services.chat import ChatService


@pytest.fixture
async def test_client():
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


@pytest.fixture
def mock_audio_service():
    service = AsyncMock()
    service.transcribe.return_value = "Gastei cinquenta reais no mercado"
    app.dependency_overrides[get_audio_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_audio_service, None)


@pytest.fixture
def mock_chat_service():
    service = AsyncMock(spec=ChatService)
    service.process_message.return_value = ChatResponse(
        response="Anotado!",
        session_id="session-audio",
        history=[],
        is_complete=False,
    )
    app.dependency_overrides[get_chat_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_chat_service, None)


@pytest.mark.asyncio
async def test_process_audio_uses_transcription_and_keeps_contract(
    test_client, mock_audio_service, mock_chat_service
):
    files = {"file": ("voice.ogg", b"fake audio", "audio/ogg")}
    data = {"session_id": "session-audio", "platform": "telegram"}

    response = await test_client.post("/audio/process-audio", files=files, data=data)

    assert response.status_code == 200
    assert response.json()["session_id"] == "session-audio"
    mock_audio_service.transcribe.assert_awaited_once_with(b"fake audio")
    mock_chat_service.process_message.assert_awaited_once_with(
        "Gastei cinquenta reais no mercado",
        "session-audio",
        "telegram",
    )


@pytest.mark.asyncio
async def test_process_audio_rejects_oversized_file(test_client, mock_audio_service):
    files = {"file": ("voice.ogg", b"x" * (10 * 1024 * 1024 + 1), "audio/ogg")}

    response = await test_client.post("/audio/process-audio", files=files)

    assert response.status_code == 400
    mock_audio_service.transcribe.assert_not_awaited()
