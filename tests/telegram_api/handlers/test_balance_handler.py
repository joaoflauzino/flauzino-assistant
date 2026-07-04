from unittest.mock import AsyncMock, patch
import pytest
from telegram import Update, Message, User, Chat, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler

from telegram_api.handlers.balance_handler import (
    balance_command,
    select_category,
    cancel,
    SELECT_CATEGORY,
)


@pytest.fixture
def mock_update():
    update = AsyncMock(spec=Update)
    update.effective_user = User(id=12345, first_name="Test", is_bot=False)
    update.effective_chat = Chat(id=67890, type="private")
    update.message = AsyncMock(spec=Message)
    update.message.reply_text = AsyncMock()

    query = AsyncMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update.callback_query = query

    return update


@pytest.fixture
def mock_context():
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    return context


@pytest.mark.asyncio
@patch("telegram_api.handlers.balance_handler.get_valid_categories")
async def test_balance_command(mock_get_categories, mock_update, mock_context):
    # Arrange
    mock_get_categories.return_value = ["mercado", "lazer"]

    # Act
    state = await balance_command(mock_update, mock_context)

    # Assert
    assert state == SELECT_CATEGORY
    mock_update.message.reply_text.assert_called_once()
    args, kwargs = mock_update.message.reply_text.call_args
    assert "Selecione as categorias que deseja visualizar:" in args[0]

    # Check reply_markup
    reply_markup = kwargs.get("reply_markup")
    assert reply_markup is not None

    # There should be buttons for "mercado", "lazer", and "Todas as Categorias"
    inline_keyboard = reply_markup.inline_keyboard
    buttons = [btn.text for row in inline_keyboard for btn in row]
    assert "mercado" in buttons
    assert "lazer" in buttons
    assert "✅ Todas" in buttons


@pytest.mark.asyncio
async def test_select_category_all(mock_update, mock_context):
    # Arrange
    mock_update.callback_query.data = "all"
    mock_context.user_data = {
        "available_categories": ["mercado", "lazer"],
        "selected_categories": set(),
    }

    # Act
    state = await select_category(mock_update, mock_context)

    # Assert
    assert state == SELECT_CATEGORY
    mock_update.callback_query.answer.assert_called_once()

    # It should have updated the keyboard
    mock_update.callback_query.edit_message_reply_markup.assert_called_once()
    assert mock_context.user_data["selected_categories"] == {"mercado", "lazer"}


@pytest.mark.asyncio
async def test_select_category_filtered(mock_update, mock_context):
    # Arrange
    mock_update.callback_query.data = "cat:mercado"
    mock_context.user_data = {
        "available_categories": ["mercado", "lazer"],
        "selected_categories": set(),
    }

    # Act
    state = await select_category(mock_update, mock_context)

    # Assert
    assert state == SELECT_CATEGORY
    mock_update.callback_query.answer.assert_called_once()

    # It should add mercado to selected
    assert mock_context.user_data["selected_categories"] == {"mercado"}
    mock_update.callback_query.edit_message_reply_markup.assert_called_once()


@pytest.mark.asyncio
@patch("telegram_api.handlers.balance_handler.httpx.AsyncClient")
async def test_select_category_empty(mock_async_client, mock_update, mock_context):
    # Arrange
    mock_update.callback_query.data = "generate"
    mock_context.user_data = {
        "available_categories": ["mercado", "lazer"],
        "selected_categories": {"mercado"},
    }

    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_async_client.return_value = mock_client_instance

    # Act
    state = await select_category(mock_update, mock_context)

    # Assert
    assert state == ConversationHandler.END

    calls = mock_update.callback_query.edit_message_text.call_args_list
    final_text = calls[1].kwargs.get("text", calls[1].args[0] if calls[1].args else "")
    assert "Você ainda não possui limites de gastos cadastrados para este mês." in final_text


@pytest.mark.asyncio
async def test_cancel(mock_update, mock_context):
    # Act
    state = await cancel(mock_update, mock_context)

    # Assert
    assert state == ConversationHandler.END
    mock_update.message.reply_text.assert_called_once_with("Consulta cancelada.")
