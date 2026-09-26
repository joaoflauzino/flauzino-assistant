from unittest.mock import AsyncMock, patch
import pytest

from telegram_api.services.session_service import SessionService


@pytest.mark.asyncio
@patch("telegram_api.services.session_service.get_db")
@patch("telegram_api.services.session_service.SessionRepository")
async def test_session_service_get_session(mock_repo_cls, mock_get_db):
    mock_session = AsyncMock()
    mock_get_db.return_value.__aenter__.return_value = mock_session

    mock_repo = AsyncMock()
    mock_repo.get_session.return_value = "session-123"
    mock_repo_cls.return_value = mock_repo

    result = await SessionService.get_session(chat_id=12345)
    assert result == "session-123"
    mock_repo.get_session.assert_called_once_with(12345)


@pytest.mark.asyncio
@patch("telegram_api.services.session_service.get_db")
@patch("telegram_api.services.session_service.SessionRepository")
async def test_session_service_sync_session_complete(mock_repo_cls, mock_get_db):
    mock_session = AsyncMock()
    mock_get_db.return_value.__aenter__.return_value = mock_session

    mock_repo = AsyncMock()
    mock_repo_cls.return_value = mock_repo

    response_data = {"is_complete": True, "session_id": "session-123"}
    await SessionService.sync_session(chat_id=12345, response_data=response_data)

    mock_repo.delete_session.assert_called_once_with(12345)
    mock_repo.save_session.assert_not_called()


@pytest.mark.asyncio
@patch("telegram_api.services.session_service.get_db")
@patch("telegram_api.services.session_service.SessionRepository")
async def test_session_service_sync_session_incomplete(mock_repo_cls, mock_get_db):
    mock_session = AsyncMock()
    mock_get_db.return_value.__aenter__.return_value = mock_session

    mock_repo = AsyncMock()
    mock_repo_cls.return_value = mock_repo

    response_data = {"is_complete": False, "session_id": "session-456"}
    await SessionService.sync_session(chat_id=12345, response_data=response_data)

    mock_repo.delete_session.assert_not_called()
    mock_repo.save_session.assert_called_once_with(12345, "session-456")
