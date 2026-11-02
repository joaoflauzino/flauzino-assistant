"""Unit tests for the shared agent interaction flow."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from telegram_api.services.agent_interaction import (
    InteractionMessages,
    handle_agent_interaction,
    reply_with_response,
    run_agent_call,
)

MESSAGES = InteractionMessages(
    fallback="fallback",
    http_error="http error",
    connection_error="connection error",
    unexpected_error="unexpected error",
)

SESSION_PATH = "telegram_api.services.agent_interaction.SessionService"
SENDER_PATH = "telegram_api.services.agent_interaction.send_agent_reply"


def http_status_error() -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "http://agent/chat")
    response = httpx.Response(500, request=request, text="boom")
    return httpx.HTTPStatusError("boom", request=request, response=response)


@pytest.mark.asyncio
async def test_run_agent_call_binds_the_session_and_syncs_the_response():
    response_data = {"response": "ok"}
    call = AsyncMock(return_value=response_data)

    with patch(SESSION_PATH) as session_service:
        session_service.get_session = AsyncMock(return_value="telegram_1")
        session_service.sync_session = AsyncMock()

        result = await run_agent_call(42, call)

    assert result == response_data
    session_service.get_session.assert_awaited_once_with(42)
    call.assert_awaited_once_with("telegram_1")
    session_service.sync_session.assert_awaited_once_with(42, response_data)


@pytest.mark.asyncio
async def test_reply_with_response_uses_the_fallback_text_and_image():
    target = AsyncMock()

    with patch(SENDER_PATH, new=AsyncMock()) as send:
        await reply_with_response(
            target,
            {"image_base64": "b64"},
            MESSAGES,
            with_options=True,
        )

    _, kwargs = send.call_args
    assert kwargs["text"] == "fallback"
    assert kwargs["image_base64"] == "b64"
    assert kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_reply_with_response_builds_the_options_keyboard_when_asked():
    target = AsyncMock()

    with patch(SENDER_PATH, new=AsyncMock()) as send:
        await reply_with_response(
            target,
            {"response": "ok", "suggested_options": ["Sim", "Não"]},
            MESSAGES,
            with_options=True,
        )

    _, kwargs = send.call_args
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_reply_with_response_ignores_options_by_default():
    target = AsyncMock()

    with patch(SENDER_PATH, new=AsyncMock()) as send:
        await reply_with_response(
            target,
            {"response": "ok", "suggested_options": ["Sim"]},
            MESSAGES,
        )

    _, kwargs = send.call_args
    assert kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_handle_agent_interaction_replies_on_success():
    target = AsyncMock()

    async def call(session_id: str | None) -> dict:
        return {"response": "resposta"}

    with (
        patch(SESSION_PATH) as session_service,
        patch(SENDER_PATH, new=AsyncMock()) as send,
    ):
        session_service.get_session = AsyncMock(return_value="telegram_1")
        session_service.sync_session = AsyncMock()

        await handle_agent_interaction(target, 42, call, MESSAGES)

    send.assert_awaited_once()
    target.reply_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_agent_interaction_maps_http_status_errors():
    target = AsyncMock()

    async def call(session_id: str | None) -> dict:
        raise http_status_error()

    with patch(SESSION_PATH) as session_service:
        session_service.get_session = AsyncMock(return_value=None)
        session_service.sync_session = AsyncMock()

        await handle_agent_interaction(target, 42, call, MESSAGES)

    target.reply_text.assert_awaited_once_with("http error")


@pytest.mark.asyncio
async def test_handle_agent_interaction_maps_connection_errors():
    target = AsyncMock()

    async def call(session_id: str | None) -> dict:
        raise httpx.ConnectError("refused")

    with patch(SESSION_PATH) as session_service:
        session_service.get_session = AsyncMock(return_value=None)
        session_service.sync_session = AsyncMock()

        await handle_agent_interaction(target, 42, call, MESSAGES)

    target.reply_text.assert_awaited_once_with("connection error")


@pytest.mark.asyncio
async def test_handle_agent_interaction_maps_unexpected_errors():
    target = AsyncMock()

    async def call(session_id: str | None) -> dict:
        raise RuntimeError("bug")

    with patch(SESSION_PATH) as session_service:
        session_service.get_session = AsyncMock(return_value=None)
        session_service.sync_session = AsyncMock()

        await handle_agent_interaction(target, 42, call, MESSAGES)

    target.reply_text.assert_awaited_once_with("unexpected error")
