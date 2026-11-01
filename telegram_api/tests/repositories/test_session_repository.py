import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram_api.models.session import TelegramSession
from telegram_api.repositories.session_repository import SessionRepository


@pytest.mark.asyncio
async def test_get_session_not_found():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    repo = SessionRepository(mock_db)
    res = await repo.get_session(chat_id=123)
    assert res is None


@pytest.mark.asyncio
async def test_get_session_active_not_expired():
    mock_db = AsyncMock()
    session_id = uuid.uuid4()
    now = datetime.now(UTC)

    session_record = TelegramSession(
        chat_id=123,
        session_id=session_id,
        created_at=now - timedelta(minutes=5),
        updated_at=now - timedelta(minutes=5),
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = session_record
    mock_db.execute.return_value = mock_result

    repo = SessionRepository(mock_db)
    res = await repo.get_session(chat_id=123, ttl_minutes=30)
    assert res == str(session_id)
    mock_db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_get_session_expired():
    mock_db = AsyncMock()
    session_id = uuid.uuid4()
    now = datetime.now(UTC)

    session_record = TelegramSession(
        chat_id=123,
        session_id=session_id,
        created_at=now - timedelta(minutes=45),
        updated_at=now - timedelta(minutes=35),  # > 30 min inactive
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = session_record
    mock_db.execute.return_value = mock_result

    repo = SessionRepository(mock_db)
    res = await repo.get_session(chat_id=123, ttl_minutes=30)

    assert res is None
    mock_db.delete.assert_called_once_with(session_record)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_and_delete_session():
    mock_db = AsyncMock()
    repo = SessionRepository(mock_db)

    # Save session
    session_id = str(uuid.uuid4())
    await repo.save_session(chat_id=123, session_id=session_id)
    assert mock_db.execute.called
    assert mock_db.commit.called

    # Delete session
    await repo.delete_session(chat_id=123)
    assert mock_db.execute.call_count == 2


@pytest.mark.asyncio
async def test_list_distinct_chat_ids_and_error_handling():
    mock_db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [111, 222]
    mock_res = MagicMock()
    mock_res.scalars.return_value = scalars_mock
    mock_db.execute.return_value = mock_res

    repo = SessionRepository(mock_db)
    chat_ids = await repo.list_distinct_chat_ids()
    assert chat_ids == [111, 222]

    # DB failure fallback
    mock_db.execute.side_effect = RuntimeError("DB failure")
    assert await repo.list_distinct_chat_ids() == []
    assert await repo.get_session(chat_id=111) is None
    await repo.save_session(chat_id=111, session_id=str(uuid.uuid4()))
    await repo.delete_session(chat_id=111)
    assert mock_db.rollback.await_count >= 2
