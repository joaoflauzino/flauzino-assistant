import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from telegram import Update, Message, User, Chat, PhotoSize
from telegram.ext import ContextTypes

from telegram_api.handlers.photo_handler import handle_photo_message


@pytest.fixture
def mock_photo_update():
    update = AsyncMock(spec=Update)
    update.effective_user = User(id=12345, first_name="Test", is_bot=False)
    update.effective_chat = Chat(id=67890, type="private")

    msg = AsyncMock(spec=Message)
    photo_size = MagicMock(spec=PhotoSize)
    photo_size.file_id = "test_photo_file_id"

    msg.photo = [photo_size]
    msg.reply_text = AsyncMock()
    msg.chat = AsyncMock()
    msg.chat.send_action = AsyncMock()
    update.message = msg

    return update


@pytest.fixture
def mock_context():
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_file = AsyncMock()
    mock_file.download_to_memory = AsyncMock(side_effect=lambda buf: buf.write(b"fake_image_bytes"))
    context.bot.get_file = AsyncMock(return_value=mock_file)
    return context


@pytest.mark.asyncio
@patch("telegram_api.handlers.photo_handler.get_db")
@patch("telegram_api.handlers.photo_handler.SessionRepository")
@patch("telegram_api.handlers.photo_handler.send_receipt_to_agent")
async def test_handle_photo_message_success(
    mock_send, mock_repo_class, mock_get_db, mock_photo_update, mock_context
):
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_get_db.return_value = mock_session

    mock_repo = AsyncMock()
    mock_repo.get_session.return_value = str(uuid.uuid4())
    mock_repo_class.return_value = mock_repo

    mock_send.return_value = {
        "response": "✅ Gasto registrado:\n- **Item:** Carne\n- **Pagamento:** c6_joao",
        "is_complete": True,
        "session_id": str(uuid.uuid4()),
    }

    await handle_photo_message(mock_photo_update, mock_context)

    mock_photo_update.message.reply_text.assert_called_once()
    args, kwargs = mock_photo_update.message.reply_text.call_args
    # Formatted with HTML
    assert "<b>Item:</b>" in args[0]
    assert "c6_joao" in args[0]
    assert kwargs.get("parse_mode") == "HTML"
