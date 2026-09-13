import uuid
from unittest.mock import AsyncMock, patch
import pytest
from telegram import Update, Message, User, Chat, CallbackQuery
from telegram.ext import ContextTypes

from telegram_api.handlers.message_handler import handle_text_message, handle_agent_callback


@pytest.fixture
def mock_update():
    update = AsyncMock(spec=Update)
    update.effective_user = User(id=12345, first_name="Test", is_bot=False)
    update.effective_chat = Chat(id=67890, type="private")

    # Message Mock
    msg = AsyncMock(spec=Message)
    msg.text = "Hello"
    msg.reply_text = AsyncMock()
    msg.chat = AsyncMock()
    msg.chat.send_action = AsyncMock()
    update.message = msg

    # CallbackQuery Mock
    query = AsyncMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.data = "agent_opt:mercado"
    query.message = msg
    update.callback_query = query

    return update


@pytest.fixture
def mock_context():
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    return context


@pytest.mark.asyncio
@patch("telegram_api.handlers.message_handler.get_db")
@patch("telegram_api.handlers.message_handler.SessionRepository")
@patch("telegram_api.handlers.message_handler.send_message_to_agent")
async def test_handle_text_message_suggested_options(
    mock_send, mock_repo_class, mock_get_db, mock_update, mock_context
):
    # Arrange
    # Mock DB Session
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_get_db.return_value = mock_session

    # Mock Repo
    mock_repo = AsyncMock()
    mock_repo.get_session.return_value = str(uuid.uuid4())
    mock_repo_class.return_value = mock_repo

    # Mock Agent API response
    mock_send.return_value = {
        "response": "Escolha uma categoria",
        "is_complete": False,
        "session_id": str(uuid.uuid4()),
        "suggested_options": ["mercado", "lazer", "Todas as categorias"],
    }

    # Act
    await handle_text_message(mock_update, mock_context)

    # Assert
    mock_update.message.reply_text.assert_called_once()

    # Verify the reply text and inline keyboard markup
    args, kwargs = mock_update.message.reply_text.call_args
    assert "Escolha uma categoria" in args[0]

    reply_markup = kwargs.get("reply_markup")
    assert reply_markup is not None

    inline_keyboard = reply_markup.inline_keyboard
    buttons = [btn.text for row in inline_keyboard for btn in row]
    assert "mercado" in buttons
    assert "lazer" in buttons
    assert "Todas as categorias" in buttons


@pytest.mark.asyncio
@patch("telegram_api.handlers.message_handler.get_db")
@patch("telegram_api.handlers.message_handler.SessionRepository")
@patch("telegram_api.handlers.message_handler.send_message_to_agent")
async def test_handle_agent_callback(
    mock_send, mock_repo_class, mock_get_db, mock_update, mock_context
):
    # Arrange
    # Mock DB Session
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_get_db.return_value = mock_session

    # Mock Repo
    mock_repo = AsyncMock()
    mock_repo.get_session.return_value = str(uuid.uuid4())
    mock_repo_class.return_value = mock_repo

    # Mock Agent API response
    mock_send.return_value = {
        "response": "Buscando saldos para o mercado...",
        "is_complete": True,
        "session_id": str(uuid.uuid4()),
    }

    # Act
    await handle_agent_callback(mock_update, mock_context)

    # Assert
    mock_update.callback_query.answer.assert_called_once()

    # Should have replied to query.message with the selection
    calls = mock_update.callback_query.message.reply_text.call_args_list
    assert len(calls) == 2
    assert "Você selecionou: mercado" in calls[0].args[0]
    assert "Buscando saldos para o mercado..." in calls[1].args[0]

    # Verify agent was called with "mercado"
    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == "mercado"
