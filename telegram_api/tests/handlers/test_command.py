from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram_api.handlers.command import help_command, start_command


@pytest.mark.asyncio
async def test_start_command_replies_with_welcome_message() -> None:
    update = MagicMock()
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()

    await start_command(update, MagicMock())

    update.message.reply_text.assert_awaited_once()
    assert "/gasto" in update.message.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_start_command_returns_when_required_update_data_is_missing() -> None:
    update = MagicMock()
    update.effective_user = None
    update.message.reply_text = AsyncMock()

    await start_command(update, MagicMock())

    update.message.reply_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_help_command_replies_with_markdown_help() -> None:
    update = MagicMock()
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()

    await help_command(update, MagicMock())

    update.message.reply_text.assert_awaited_once()
    assert update.message.reply_text.await_args.kwargs["parse_mode"] == "Markdown"


@pytest.mark.asyncio
async def test_help_command_returns_when_message_is_missing() -> None:
    update = MagicMock()
    update.effective_user.id = 123
    update.message = None

    await help_command(update, MagicMock())
