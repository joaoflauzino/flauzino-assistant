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
    assert "Qual categoria você deseja consultar?" in args[0]

    # Check reply_markup
    reply_markup = kwargs.get("reply_markup")
    assert reply_markup is not None

    # There should be buttons for "mercado", "lazer", and "Todas as Categorias"
    inline_keyboard = reply_markup.inline_keyboard
    buttons = [btn.text for row in inline_keyboard for btn in row]
    assert "mercado" in buttons
    assert "lazer" in buttons
    assert "Todas as Categorias" in buttons


@pytest.mark.asyncio
@patch("telegram_api.handlers.balance_handler.httpx.AsyncClient")
async def test_select_category_all(mock_async_client, mock_update, mock_context):
    # Arrange
    mock_update.callback_query.data = "Todas as Categorias"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: [
        {
            "category": "mercado",
            "category_display_name": "Mercado",
            "limit": 1000.0,
            "spent": 500.0,
            "available": 500.0,
            "percentage_used": 50.0,
        }
    ]
    mock_response.raise_for_status = lambda: None

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_async_client.return_value = mock_client_instance

    # Act
    state = await select_category(mock_update, mock_context)

    # Assert
    assert state == ConversationHandler.END
    mock_update.callback_query.answer.assert_called_once()

    # Check edit_message_text calls
    calls = mock_update.callback_query.edit_message_text.call_args_list
    assert len(calls) == 2

    # First call is loading
    assert "Consultando saldos" in calls[0].kwargs.get(
        "text", calls[0].args[0] if calls[0].args else ""
    )

    # Second call is result
    final_text = calls[1].kwargs.get("text", calls[1].args[0] if calls[1].args else "")
    assert "Mercado" in final_text
    assert "R$ 1000.00" in final_text
    assert "R$ 500.00" in final_text


@pytest.mark.asyncio
@patch("telegram_api.handlers.balance_handler.httpx.AsyncClient")
async def test_select_category_filtered(mock_async_client, mock_update, mock_context):
    # Arrange
    mock_update.callback_query.data = "mercado"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: [
        {
            "category": "mercado",
            "category_display_name": "Mercado",
            "limit": 1000.0,
            "spent": 500.0,
            "available": 500.0,
            "percentage_used": 50.0,
        },
        {
            "category": "lazer",
            "category_display_name": "Lazer",
            "limit": 200.0,
            "spent": 200.0,
            "available": 0.0,
            "percentage_used": 100.0,
        },
    ]
    mock_response.raise_for_status = lambda: None

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_async_client.return_value = mock_client_instance

    # Act
    state = await select_category(mock_update, mock_context)

    # Assert
    assert state == ConversationHandler.END

    # Check edit_message_text calls
    calls = mock_update.callback_query.edit_message_text.call_args_list

    final_text = calls[1].kwargs.get("text", calls[1].args[0] if calls[1].args else "")
    assert "Mercado" in final_text
    assert "Lazer" not in final_text


@pytest.mark.asyncio
@patch("telegram_api.handlers.balance_handler.httpx.AsyncClient")
async def test_select_category_empty(mock_async_client, mock_update, mock_context):
    # Arrange
    mock_update.callback_query.data = "Todas as Categorias"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: []
    mock_response.raise_for_status = lambda: None

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
