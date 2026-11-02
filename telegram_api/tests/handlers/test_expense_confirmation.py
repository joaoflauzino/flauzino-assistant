from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import CallbackQuery, Message
from telegram.ext import ConversationHandler

from telegram_api.handlers.expense_confirmation import (
    ask_for_date,
    select_date_option,
    show_confirmation,
    type_custom_date,
)
from telegram_api.handlers.expense_states import CONFIRMATION, SELECT_DATE_OPTION, TYPE_CUSTOM_DATE


@pytest.mark.asyncio
async def test_ask_for_date_replies_to_message() -> None:
    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()

    state = await ask_for_date(message, MagicMock())

    assert state == SELECT_DATE_OPTION
    message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_ask_for_date_edits_callback_message() -> None:
    query = MagicMock(spec=CallbackQuery)
    query.edit_message_text = AsyncMock()

    state = await ask_for_date(query, MagicMock())

    assert state == SELECT_DATE_OPTION
    query.edit_message_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_select_date_option_returns_when_callback_or_user_data_is_missing() -> None:
    update = MagicMock()
    update.callback_query = None
    assert await select_date_option(update, MagicMock(user_data={})) == SELECT_DATE_OPTION

    update.callback_query = MagicMock(spec=CallbackQuery)
    assert await select_date_option(update, MagicMock(user_data=None)) == SELECT_DATE_OPTION


@pytest.mark.asyncio
async def test_select_custom_date_prompts_for_text() -> None:
    query = MagicMock(spec=CallbackQuery)
    query.data = "date_custom"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock(callback_query=query)

    state = await select_date_option(update, MagicMock(user_data={"expense": {}}))

    assert state == TYPE_CUSTOM_DATE
    query.edit_message_text.assert_awaited_once()


@pytest.mark.parametrize("option", ["date_hoje", "date_ontem"])
@pytest.mark.asyncio
async def test_select_relative_date_sets_date_and_confirms(option: str) -> None:
    query = MagicMock(spec=CallbackQuery)
    query.data = option
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    expense = {
        "category": "mercado",
        "item_bought": "frutas",
        "amount": 25.5,
        "payment_method": "pix_joao",
    }

    state = await select_date_option(
        MagicMock(callback_query=query),
        MagicMock(user_data={"expense": expense}),
    )

    assert state == CONFIRMATION
    assert isinstance(expense["created_at"], datetime)
    query.edit_message_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_select_unknown_date_option_keeps_date_selection_active() -> None:
    query = MagicMock(spec=CallbackQuery)
    query.data = "unknown"
    query.answer = AsyncMock()

    state = await select_date_option(
        MagicMock(callback_query=query),
        MagicMock(user_data={"expense": {}}),
    )

    assert state == SELECT_DATE_OPTION
    query.edit_message_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_custom_date_returns_when_message_or_context_is_missing() -> None:
    update = MagicMock()
    update.message = None
    assert await type_custom_date(update, MagicMock(user_data={"expense": {}})) == TYPE_CUSTOM_DATE

    message = MagicMock(spec=Message)
    message.text = None
    update.message = message
    assert await type_custom_date(update, MagicMock(user_data={"expense": {}})) == TYPE_CUSTOM_DATE
    assert await type_custom_date(update, MagicMock(user_data=None)) == TYPE_CUSTOM_DATE


@pytest.mark.asyncio
async def test_custom_date_sets_expense_date_and_shows_confirmation() -> None:
    message = MagicMock(spec=Message)
    message.text = "15/06/2026"
    message.reply_text = AsyncMock()
    expense = {
        "category": "mercado",
        "item_bought": "frutas",
        "amount": 25.5,
        "payment_method": "pix_joao",
    }
    context = MagicMock(user_data={"expense": expense})

    state = await type_custom_date(MagicMock(message=message), context)

    assert state == CONFIRMATION
    assert isinstance(expense["created_at"], datetime)
    message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_custom_date_rejects_invalid_format() -> None:
    message = MagicMock(spec=Message)
    message.text = "2026-06-15"
    message.reply_text = AsyncMock()

    state = await type_custom_date(
        MagicMock(message=message),
        MagicMock(user_data={"expense": {}}),
    )

    assert state == TYPE_CUSTOM_DATE
    message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_show_confirmation_ends_when_user_data_is_missing() -> None:
    assert (
        await show_confirmation(MagicMock(spec=Message), MagicMock(user_data=None))
        == ConversationHandler.END
    )


@pytest.mark.asyncio
async def test_show_confirmation_edits_callback_message() -> None:
    query = MagicMock(spec=CallbackQuery)
    query.edit_message_text = AsyncMock()
    expense = {
        "category": "mercado",
        "item_bought": "frutas",
        "amount": 25.5,
        "payment_method": "pix_joao",
    }

    state = await show_confirmation(query, MagicMock(user_data={"expense": expense}))

    assert state == CONFIRMATION
    query.edit_message_text.assert_awaited_once()
