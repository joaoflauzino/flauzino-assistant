from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from telegram.ext import ApplicationHandlerStop

from telegram_api.core import middleware
from telegram_api.core.metrics import TELEGRAM_MESSAGES_RECEIVED_TOTAL

SETTINGS_PATH = "telegram_api.core.middleware.settings"


def _message(**overrides) -> SimpleNamespace:
    defaults = {
        "text": None,
        "photo": [],
        "voice": None,
        "audio": None,
        "reply_text": AsyncMock(),
    }
    return SimpleNamespace(**(defaults | overrides))


def _update(
    message: SimpleNamespace | None = None,
    callback_query: SimpleNamespace | None = None,
    username: str | None = "joao",
) -> SimpleNamespace:
    user = SimpleNamespace(id=1, username=username) if username is not None else None
    return SimpleNamespace(message=message, callback_query=callback_query, effective_user=user)


def _counter(message_type: str) -> float:
    return TELEGRAM_MESSAGES_RECEIVED_TOTAL.labels(type=message_type)._value.get()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "expected_type"),
    [
        (_message(text="/gasto"), "command"),
        (_message(text="olá"), "text"),
        (_message(photo=["file-id"]), "photo"),
        (_message(voice={"duration": 1}), "voice"),
        (_message(audio={"duration": 1}), "voice"),
        (_message(), "unknown"),
    ],
)
@patch(SETTINGS_PATH)
async def test_records_detected_message_type(mock_settings, message, expected_type):
    mock_settings.ALLOWED_TELEGRAM_USERNAMES = "joao"
    before = _counter(expected_type)

    await middleware.auth_middleware(_update(message=message), AsyncMock())

    assert _counter(expected_type) == before + 1


@pytest.mark.asyncio
@patch(SETTINGS_PATH)
async def test_records_callback_query_type(mock_settings):
    mock_settings.ALLOWED_TELEGRAM_USERNAMES = "joao"
    before = _counter("callback_query")

    await middleware.auth_middleware(_update(callback_query=SimpleNamespace()), AsyncMock())

    assert _counter("callback_query") == before + 1


@pytest.mark.asyncio
@patch(SETTINGS_PATH)
async def test_allows_authorized_user(mock_settings):
    mock_settings.ALLOWED_TELEGRAM_USERNAMES = "lailla, JOAO"
    message = _message(text="oi")

    await middleware.auth_middleware(_update(message=message, username="Joao"), AsyncMock())

    message.reply_text.assert_not_awaited()


@pytest.mark.asyncio
@patch(SETTINGS_PATH)
async def test_denies_user_outside_allow_list(mock_settings):
    mock_settings.ALLOWED_TELEGRAM_USERNAMES = "joao"
    message = _message(text="oi")
    before = _counter("unauthorized")

    with pytest.raises(ApplicationHandlerStop):
        await middleware.auth_middleware(_update(message=message, username="intruso"), AsyncMock())

    message.reply_text.assert_awaited_once_with(middleware.DENIED_MESSAGE)
    assert _counter("unauthorized") == before + 1


@pytest.mark.asyncio
@patch(SETTINGS_PATH)
async def test_denies_user_without_username(mock_settings):
    mock_settings.ALLOWED_TELEGRAM_USERNAMES = "joao"
    message = _message(text="oi")

    with pytest.raises(ApplicationHandlerStop):
        await middleware.auth_middleware(_update(message=message, username=None), AsyncMock())

    message.reply_text.assert_awaited_once_with(middleware.DENIED_MESSAGE)


@pytest.mark.asyncio
@patch(SETTINGS_PATH)
async def test_skips_authorization_when_allow_list_is_empty(mock_settings):
    mock_settings.ALLOWED_TELEGRAM_USERNAMES = ""
    message = _message(text="oi")

    await middleware.auth_middleware(_update(message=message, username="intruso"), AsyncMock())

    message.reply_text.assert_not_awaited()


@pytest.mark.asyncio
@patch(SETTINGS_PATH)
async def test_skips_authorization_without_effective_user(mock_settings):
    mock_settings.ALLOWED_TELEGRAM_USERNAMES = "joao"
    message = _message(text="oi")
    update = _update(message=message)
    update.effective_user = None

    await middleware.auth_middleware(update, AsyncMock())

    message.reply_text.assert_not_awaited()


@pytest.mark.asyncio
@patch(SETTINGS_PATH)
async def test_denies_user_when_allow_list_has_only_separators(mock_settings):
    mock_settings.ALLOWED_TELEGRAM_USERNAMES = ", ,"
    message = _message(text="oi")

    with pytest.raises(ApplicationHandlerStop):
        await middleware.auth_middleware(_update(message=message, username="joao"), AsyncMock())
