"""Unit tests for the shared HTTP retry policy."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from telegram_api.core.http_client import post_with_retry


def ok_response() -> MagicMock:
    response = MagicMock()
    response.raise_for_status = Mock()
    return response


@pytest.mark.asyncio
async def test_post_with_retry_returns_the_first_successful_response():
    response = ok_response()
    request = AsyncMock(return_value=response)

    result = await post_with_retry(request)

    assert result is response
    request.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_with_retry_retries_with_exponential_backoff():
    response = ok_response()
    calls = 0

    async def request() -> MagicMock:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ConnectError("connection refused")
        return response

    with patch("telegram_api.core.http_client.asyncio.sleep", new=AsyncMock()) as sleep:
        result = await post_with_retry(request)

    assert result is response
    assert calls == 3
    assert [call.args[0] for call in sleep.await_args_list] == [1.0, 2.0]


@pytest.mark.asyncio
async def test_post_with_retry_reraises_after_the_last_attempt():
    async def request() -> MagicMock:
        raise httpx.ConnectError("connection refused")

    with patch("telegram_api.core.http_client.asyncio.sleep", new=AsyncMock()) as sleep:
        with pytest.raises(httpx.ConnectError):
            await post_with_retry(request, attempts=3)

    assert sleep.await_count == 2


@pytest.mark.asyncio
async def test_post_with_retry_honours_a_custom_attempt_budget():
    async def request() -> MagicMock:
        raise httpx.TimeoutException("timeout")

    with patch("telegram_api.core.http_client.asyncio.sleep", new=AsyncMock()) as sleep:
        with pytest.raises(httpx.TimeoutException):
            await post_with_retry(request, attempts=1)

    sleep.assert_not_awaited()
