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
    mock_repo.get_session.assert_called_once_with(12345, ttl_minutes=30)


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


@pytest.mark.asyncio
async def test_session_service_with_injected_repository_protocol():
    fake_repo = AsyncMock()
    fake_repo.get_session.return_value = "injected-sess-1"
    fake_repo.list_distinct_chat_ids.return_value = [1001, 1002]

    service = SessionService(repository=fake_repo)

    active = await service.get_active_session(chat_id=1001, ttl_minutes=15)
    assert active == "injected-sess-1"
    fake_repo.get_session.assert_awaited_once_with(1001, ttl_minutes=15)

    await service.sync_chat_session(1001, {"is_complete": False, "session_id": "new-sess"})
    fake_repo.save_session.assert_awaited_once_with(1001, "new-sess")

    await service.sync_chat_session(1001, {"is_complete": True})
    fake_repo.delete_session.assert_awaited_once_with(1001)

    chat_ids = await service.list_known_chat_ids()
    assert chat_ids == [1001, 1002]


@pytest.mark.asyncio
@patch("telegram_api.services.session_service.get_db")
@patch("telegram_api.services.session_service.SessionRepository")
async def test_session_service_list_known_chat_ids_default_db(mock_repo_cls, mock_get_db):
    mock_session = AsyncMock()
    mock_get_db.return_value.__aenter__.return_value = mock_session

    mock_repo = AsyncMock()
    mock_repo.list_distinct_chat_ids.return_value = [999]
    mock_repo_cls.return_value = mock_repo

    service = SessionService()
    assert await service.list_known_chat_ids() == [999]


@pytest.mark.asyncio
async def test_sync_chat_session_noop_without_flags_injected_repo():
    fake_repo = AsyncMock()
    service = SessionService(repository=fake_repo)

    await service.sync_chat_session(1001, {})

    fake_repo.delete_session.assert_not_awaited()
    fake_repo.save_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_chat_session_complete_wins_over_session_id():
    fake_repo = AsyncMock()
    service = SessionService(repository=fake_repo)

    await service.sync_chat_session(1001, {"is_complete": True, "session_id": "sess-9"})

    fake_repo.delete_session.assert_awaited_once_with(1001)
    fake_repo.save_session.assert_not_awaited()


@pytest.mark.asyncio
@patch("telegram_api.services.session_service.get_db")
@patch("telegram_api.services.session_service.SessionRepository")
async def test_sync_session_noop_without_flags_default_db(mock_repo_cls, mock_get_db):
    mock_session = AsyncMock()
    mock_get_db.return_value.__aenter__.return_value = mock_session

    mock_repo = AsyncMock()
    mock_repo_cls.return_value = mock_repo

    await SessionService.sync_session(12345, {"is_complete": False, "session_id": None})

    mock_repo.delete_session.assert_not_called()
    mock_repo.save_session.assert_not_called()
