import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from telegram_api.handlers.expense_handler import (
    gasto_command,
    select_category,
    type_item_bought,
    type_value,
    select_payment_method,
    select_owner,
    type_location,
    confirm_expense,
    cancel,
    SELECT_CATEGORY,
    TYPE_ITEM_BOUGHT,
    TYPE_VALUE,
    SELECT_PAYMENT_METHOD,
    SELECT_OWNER,
    TYPE_LOCATION,
    CONFIRMATION,
)
from telegram.ext import ConversationHandler


@pytest.fixture
def mock_update():
    update = AsyncMock()
    update.effective_user.id = 12345
    update.message = AsyncMock()
    update.message.text = "test message"
    update.callback_query = AsyncMock()
    update.callback_query.data = "test_data"
    return update


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.user_data = {}
    return context


@pytest.mark.asyncio
@patch("telegram_api.handlers.expense_handler.get_valid_categories")
async def test_gasto_command(mock_get_categories, mock_update, mock_context):
    mock_get_categories.return_value = ["categoria1", "categoria2"]

    state = await gasto_command(mock_update, mock_context)

    assert state == SELECT_CATEGORY
    assert "expense" in mock_context.user_data
    mock_update.message.reply_text.assert_called_once()
    mock_get_categories.assert_called_once()


@pytest.mark.asyncio
async def test_select_category(mock_update, mock_context):
    mock_context.user_data["expense"] = {}
    mock_update.callback_query.data = "categoria1"

    state = await select_category(mock_update, mock_context)

    assert state == TYPE_ITEM_BOUGHT
    assert mock_context.user_data["expense"]["category"] == "categoria1"
    mock_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_type_item_bought(mock_update, mock_context):
    mock_context.user_data["expense"] = {}
    mock_update.message.text = "Pizza"

    state = await type_item_bought(mock_update, mock_context)

    assert state == TYPE_VALUE
    assert mock_context.user_data["expense"]["item_bought"] == "Pizza"
    mock_update.message.reply_text.assert_called_once_with("Qual foi o valor?")


@pytest.mark.asyncio
@patch("telegram_api.handlers.expense_handler.get_valid_payment_methods")
async def test_type_value_valid(mock_get_payment, mock_update, mock_context):
    mock_get_payment.return_value = ["itau", "nubank"]
    mock_context.user_data["expense"] = {}
    mock_update.message.text = "50,50"

    state = await type_value(mock_update, mock_context)

    assert state == SELECT_PAYMENT_METHOD
    assert mock_context.user_data["expense"]["amount"] == 50.50
    mock_update.message.reply_text.assert_called_once()
    mock_get_payment.assert_called_once()


@pytest.mark.asyncio
async def test_type_value_invalid(mock_update, mock_context):
    mock_context.user_data["expense"] = {}
    mock_update.message.text = "abc"

    state = await type_value(mock_update, mock_context)

    assert state == TYPE_VALUE
    assert "amount" not in mock_context.user_data["expense"]
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch("telegram_api.handlers.expense_handler.get_valid_owners")
async def test_select_payment_method(mock_get_owners, mock_update, mock_context):
    mock_get_owners.return_value = ["joao", "maria"]
    mock_context.user_data["expense"] = {}
    mock_update.callback_query.data = "nubank"

    state = await select_payment_method(mock_update, mock_context)

    assert state == SELECT_OWNER
    assert mock_context.user_data["expense"]["payment_method"] == "nubank"
    mock_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_select_owner(mock_update, mock_context):
    mock_context.user_data["expense"] = {}
    mock_update.callback_query.data = "joao"

    state = await select_owner(mock_update, mock_context)

    assert state == TYPE_LOCATION
    assert mock_context.user_data["expense"]["payment_owner"] == "joao"
    mock_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_type_location(mock_update, mock_context):
    mock_context.user_data["expense"] = {
        "category": "cat",
        "item_bought": "item",
        "amount": 10.0,
        "payment_method": "method",
        "payment_owner": "owner",
    }
    mock_update.message.text = "Mercado"

    state = await type_location(mock_update, mock_context)

    assert state == CONFIRMATION
    assert mock_context.user_data["expense"]["location"] == "Mercado"
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch("telegram_api.handlers.expense_handler.save_spent")
async def test_confirm_expense(mock_save_spent, mock_update, mock_context):
    mock_context.user_data["expense"] = {"data": "test"}
    mock_update.callback_query.data = "confirm"

    state = await confirm_expense(mock_update, mock_context)

    assert state == ConversationHandler.END
    mock_save_spent.assert_called_once_with({"data": "test"})
    assert "expense" not in mock_context.user_data
    mock_update.callback_query.edit_message_text.assert_called_once_with(
        text="✅ Gasto registrado com sucesso!"
    )


@pytest.mark.asyncio
@patch("telegram_api.handlers.expense_handler.save_spent")
async def test_cancel_expense(mock_save_spent, mock_update, mock_context):
    mock_context.user_data["expense"] = {"data": "test"}
    mock_update.callback_query.data = "cancel"

    state = await confirm_expense(mock_update, mock_context)

    assert state == ConversationHandler.END
    mock_save_spent.assert_not_called()
    assert "expense" not in mock_context.user_data
    mock_update.callback_query.edit_message_text.assert_called_once_with(
        text="❌ Registro de gasto cancelado."
    )


@pytest.mark.asyncio
async def test_cancel(mock_update, mock_context):
    mock_context.user_data["expense"] = {"data": "test"}

    state = await cancel(mock_update, mock_context)

    assert state == ConversationHandler.END
    assert "expense" not in mock_context.user_data
    mock_update.message.reply_text.assert_called_once_with("Registro de gasto cancelado.")
