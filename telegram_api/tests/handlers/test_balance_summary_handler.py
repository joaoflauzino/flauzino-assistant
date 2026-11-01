from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from telegram_api.handlers.balance_summary_handler import balanco_command
from telegram_api.main import send_weekly_balance_summary


@pytest.fixture
def mock_update():
    update = AsyncMock()
    update.effective_user.id = 12345
    update.message = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.args = []
    context.bot = AsyncMock()
    return context


@pytest.mark.asyncio
@patch("telegram_api.handlers.balance_summary_handler.get_monthly_balance_summary")
async def test_balanco_command_success(mock_get_summary, mock_update, mock_context):
    mock_get_summary.return_value = {
        "reference_month": "2026-08",
        "total_incomes": 8500.0,
        "total_spents": 4200.0,
        "net_balance": 4300.0,
        "is_positive": True,
        "savings_rate": 50.6,
    }

    await balanco_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "8.500,00" in msg
    assert "4.200,00" in msg
    assert "4.300,00" in msg
    assert "Superávit" in msg
    assert "50.6%" in msg


@pytest.mark.asyncio
@patch("telegram_api.handlers.balance_summary_handler.get_monthly_balance_summary")
async def test_balanco_command_failure(mock_get_summary, mock_update, mock_context):
    mock_get_summary.return_value = None

    await balanco_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "Não foi possível carregar" in msg


@pytest.mark.asyncio
@patch("telegram_api.main.SessionService")
@patch("telegram_api.main.get_balance_graph")
@patch("telegram_api.main.settings")
async def test_send_weekly_balance_summary(
    mock_settings,
    mock_get_graph,
    mock_session_service_cls,
    mock_context,
):
    mock_settings.ALLOWED_TELEGRAM_USERNAMES = "joao, lailla"
    mock_get_graph.return_value = b"fake_png_bytes"

    mock_svc = AsyncMock()
    mock_svc.list_known_chat_ids.return_value = [101, 202]
    mock_session_service_cls.return_value = mock_svc

    # First chat succeeds, second raises exception (tested for resilience)
    mock_context.bot.send_photo.side_effect = [None, RuntimeError("Telegram error")]

    await send_weekly_balance_summary(mock_context)

    mock_svc.list_known_chat_ids.assert_awaited_once()
    assert mock_context.bot.send_photo.await_count == 2
