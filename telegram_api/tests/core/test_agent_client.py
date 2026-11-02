"""Unit tests for the agent_api client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from telegram_api.core.agent_client import send_message_to_agent
from telegram_api.core.correlation import CORRELATION_HEADER, set_request_id


@pytest.mark.asyncio
@patch("telegram_api.core.agent_client.get_http_client")
async def test_send_message_to_agent_includes_correlation_header(mock_get_client):
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "ok"}
    mock_client.post.return_value = mock_resp
    mock_get_client.return_value = mock_client

    set_request_id("tg-trace-xyz")
    res = await send_message_to_agent("olá")

    assert res == {"response": "ok"}
    mock_client.post.assert_called_once()
    headers = mock_client.post.call_args.kwargs.get("headers", {})
    assert headers.get(CORRELATION_HEADER) == "tg-trace-xyz"


@pytest.mark.asyncio
@patch("telegram_api.core.agent_client.get_http_client")
async def test_send_message_to_agent_forwards_the_session_id(mock_get_client):
    mock_client = AsyncMock()
    mock_client.post.return_value = MagicMock(
        raise_for_status=MagicMock(), json=MagicMock(return_value={"response": "ok"})
    )
    mock_get_client.return_value = mock_client

    await send_message_to_agent("olá", session_id="telegram_123")

    payload = mock_client.post.call_args.kwargs["json"]
    assert payload == {"message": "olá", "platform": "telegram", "session_id": "telegram_123"}
