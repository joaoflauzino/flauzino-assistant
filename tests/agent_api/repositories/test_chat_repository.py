from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from agent_api.repositories.chat_repository import ChatRepository
from agent_api.models.chat import ChatSession, ChatMessage


@pytest.fixture
def mock_db_session():
    """Fixture for a mocked async database session."""
    session = AsyncMock(spec=AsyncSession)

    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    session.add = MagicMock()

    # Define a side effect for refresh to populate ID
    async def refresh_side_effect(instance):
        if hasattr(instance, "id") and instance.id is None:
            instance.id = uuid.uuid4()

    session.refresh.side_effect = refresh_side_effect

    return session


@pytest.mark.asyncio
async def test_create_session(mock_db_session):
    repo = ChatRepository(mock_db_session)

    # Act
    session = await repo.create_session()

    # Assert
    assert session.id is not None
    assert isinstance(session, ChatSession)

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session(mock_db_session):
    repo = ChatRepository(mock_db_session)
    fake_id = uuid.uuid4()

    # Mock return value
    mock_session_obj = ChatSession(id=fake_id)
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_session_obj
    )

    # Act
    result = await repo.get_session(fake_id)

    # Assert
    assert result == mock_session_obj
    mock_db_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_message(mock_db_session):
    repo = ChatRepository(mock_db_session)
    session_id = uuid.uuid4()

    # Act
    message = await repo.add_message(session_id, "user", "Hello")

    # Assert
    assert message.session_id == session_id
    assert message.role == "user"
    assert message.content == "Hello"

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_messages(mock_db_session):
    repo = ChatRepository(mock_db_session)
    session_id = uuid.uuid4()

    # Mock return value
    # The repo queries DESC (Newest first), so we should provide them in that order logically
    # msg2 is newer than msg1
    mock_msg1 = ChatMessage(
        role="user", content="Hi", created_at=datetime.now(timezone.utc)
    )
    mock_msg2 = ChatMessage(
        role="assistant", content="Hello", created_at=datetime.now(timezone.utc)
    )

    # DB returns [Newest, Oldest] -> [msg2, msg1]
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [
        mock_msg2,
        mock_msg1,
    ]

    # Act
    messages = await repo.get_messages(session_id)

    # Assert
    assert len(messages) == 2
    # User removed reversed(), so now it returns [Newest, Oldest] -> [msg2, msg1]
    assert messages[0] == mock_msg2
    assert messages[1] == mock_msg1


@pytest.mark.asyncio
async def test_get_messages_limit(mock_db_session):
    repo = ChatRepository(mock_db_session)
    session_id = uuid.uuid4()

    # Simulate DB returning 10 messages (newest first)
    fake_messages = [
        ChatMessage(id=i, session_id=session_id, content=f"msg_{i}")
        for i in range(10, 0, -1)  # 10..1
    ]

    # The repo queries DESC + LIMIT 5.
    # So the DB would return the first 5 of that list: 10, 9, 8, 7, 6
    returned_from_db = fake_messages[:5]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = returned_from_db
    mock_db_session.execute.return_value = mock_result

    # Act
    messages = await repo.get_messages(session_id, limit=5)

    # Assert
    # User removed reversed(), so now it returns [Newest...Oldest]
    assert len(messages) == 5
    assert messages[0].content == "msg_10"
    assert messages[4].content == "msg_6"

    # Check that query contained LIMIT (rough check)
    args, _ = mock_db_session.execute.call_args
    query_str = str(args[0])
    assert "LIMIT" in query_str or "limit" in query_str
    mock_db_session.execute.assert_awaited_once()
