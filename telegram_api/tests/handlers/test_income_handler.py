from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.ext import ConversationHandler

from telegram_api.handlers.income_handler import (
    CONFIRMATION,
    SELECT_CATEGORY,
    SELECT_PAYMENT_METHOD,
    TYPE_DESCRIPTION,
    TYPE_VALUE,
    cancel_income,
    confirm_income,
    receita_command,
    select_category,
    select_payment_method,
    type_description,
    type_value,
)


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
@patch("telegram_api.handlers.income_handler.get_valid_income_categories")
async def test_receita_command(mock_get_cats, mock_update, mock_context):
    mock_get_cats.return_value = ["salario", "pix"]

    state = await receita_command(mock_update, mock_context)

    assert state == SELECT_CATEGORY
    assert "income" in mock_context.user_data
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_select_category(mock_update, mock_context):
    mock_context.user_data["income"] = {}
    mock_update.callback_query.data = "salario"

    state = await select_category(mock_update, mock_context)

    assert state == TYPE_DESCRIPTION
    assert mock_context.user_data["income"]["category"] == "salario"
    mock_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_type_description(mock_update, mock_context):
    mock_context.user_data["income"] = {}
    mock_update.message.text = "Salário Empresa"

    state = await type_description(mock_update, mock_context)

    assert state == TYPE_VALUE
    assert mock_context.user_data["income"]["description"] == "Salário Empresa"
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch("telegram_api.handlers.income_handler.get_valid_payment_methods")
async def test_type_value_success(mock_get_pm, mock_update, mock_context):
    mock_get_pm.return_value = ["itau_joao"]
    mock_context.user_data["income"] = {}
    mock_update.message.text = "5000,50"

    state = await type_value(mock_update, mock_context)

    assert state == SELECT_PAYMENT_METHOD
    assert mock_context.user_data["income"]["amount"] == 5000.50
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_type_value_invalid(mock_update, mock_context):
    mock_context.user_data["income"] = {}
    mock_update.message.text = "invalid_number"

    state = await type_value(mock_update, mock_context)

    assert state == TYPE_VALUE
    assert "amount" not in mock_context.user_data["income"]


@pytest.mark.asyncio
async def test_select_payment_method(mock_update, mock_context):
    mock_context.user_data["income"] = {
        "category": "salario",
        "description": "Salário",
        "amount": 5000.0,
    }
    mock_update.callback_query.data = "itau_joao"

    state = await select_payment_method(mock_update, mock_context)

    assert state == CONFIRMATION
    assert mock_context.user_data["income"]["payment_method"] == "itau_joao"
    mock_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
@patch("telegram_api.handlers.income_handler.save_income")
async def test_confirm_income_success(mock_save_income, mock_update, mock_context):
    mock_context.user_data["income"] = {
        "category": "salario",
        "description": "Salário",
        "amount": 5000.0,
        "payment_method": "itau_joao",
    }
    mock_update.callback_query.data = "confirm"
    mock_save_income.return_value = {"id": "123"}

    state = await confirm_income(mock_update, mock_context)

    assert state == ConversationHandler.END
    mock_save_income.assert_called_once()
    assert "income" not in mock_context.user_data


@pytest.mark.asyncio
async def test_cancel_income(mock_update, mock_context):
    mock_context.user_data["income"] = {"temp": "data"}

    state = await cancel_income(mock_update, mock_context)

    assert state == ConversationHandler.END
    assert "income" not in mock_context.user_data
    mock_update.message.reply_text.assert_called_once()
