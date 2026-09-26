import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from telegram import Update, Message, User, Chat, Voice
from telegram.ext import ContextTypes

from telegram_api.handlers.voice_handler import handle_voice_message


@pytest.fixture
def mock_voice_update():
    update = AsyncMock(spec=Update)
    update.effective_user = User(id=12345, first_name="Test", is_bot=False)
    update.effective_chat = Chat(id=67890, type="private")

    msg = AsyncMock(spec=Message)
    voice = MagicMock(spec=Voice)
    voice.file_id = "test_voice_file_id"
    voice.mime_type = "audio/ogg"

    msg.voice = voice
    msg.audio = None
    msg.reply_text = AsyncMock()
    msg.chat = AsyncMock()
    msg.chat.send_action = AsyncMock()
    update.message = msg

    return update


@pytest.fixture
def mock_context():
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_file = AsyncMock()
    mock_file.download_to_memory = AsyncMock(side_effect=lambda buf: buf.write(b"fake_voice_bytes"))
    context.bot.get_file = AsyncMock(return_value=mock_file)
    return context


@pytest.mark.asyncio
@patch("telegram_api.handlers.voice_handler.get_db")
@patch("telegram_api.handlers.voice_handler.SessionRepository")
@patch("telegram_api.handlers.voice_handler.send_audio_to_agent")
async def test_handle_voice_message_success(
    mock_send, mock_repo_class, mock_get_db, mock_voice_update, mock_context
):
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_get_db.return_value = mock_session

    mock_repo = AsyncMock()
    mock_repo.get_session.return_value = str(uuid.uuid4())
    mock_repo_class.return_value = mock_repo

    mock_send.return_value = {
        "response": "✅ Gasto registrado:\n- **Valor:** **R$ 50,00**\n- **Pagamento:** c6_joao",
        "is_complete": True,
        "session_id": str(uuid.uuid4()),
    }

    await handle_voice_message(mock_voice_update, mock_context)

    mock_voice_update.message.reply_text.assert_called_once()
    args, kwargs = mock_voice_update.message.reply_text.call_args
    # Formatted with HTML
    assert "<b>Valor:</b>" in args[0]
    assert "<b>R$ 50,00</b>" in args[0]
    assert "c6_joao" in args[0]
    assert kwargs.get("parse_mode") == "HTML"
