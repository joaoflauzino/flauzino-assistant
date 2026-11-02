"""Persistent HTTP client, correlation headers and retry policy for the Telegram bot."""

import asyncio
from collections.abc import Awaitable, Callable

import httpx

from telegram_api.core.correlation import CORRELATION_HEADER, get_request_id, set_request_id
from telegram_api.core.logger import get_logger
from telegram_api.settings import settings

logger = get_logger(__name__)

# Single persistent HTTP client - reused across all requests
_http_client: httpx.AsyncClient | None = None


def get_request_headers() -> dict[str, str]:
    """Returns the correlation header for the current request, creating an id when absent."""
    request_id = get_request_id() or set_request_id()
    return {CORRELATION_HEADER: request_id}


def get_http_client() -> httpx.AsyncClient:
    """Get or create the persistent HTTP client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.REQUEST_TIMEOUT),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return _http_client


async def close_http_client() -> None:
    """Close the persistent HTTP client."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        logger.info("HTTP client closed")


async def post_with_retry(
    request: Callable[[], Awaitable[httpx.Response]],
    *,
    attempts: int = 3,
    backoff: float = 2.0,
) -> httpx.Response:
    """Runs an HTTP request, retrying with exponential backoff until the last attempt.

    Args:
        request: Zero-argument factory returning the coroutine to await on each attempt.
        attempts: Total number of attempts before re-raising the last HTTP error.
        backoff: Base of the exponential sleep applied between attempts.

    Raises:
        httpx.HTTPError: When every attempt fails.
    """
    attempt = 0
    while True:
        try:
            response = await request()
            response.raise_for_status()
            return response
        except httpx.HTTPError as error:
            attempt += 1
            logger.warning(f"HTTP error on attempt {attempt}: {error}")
            if attempt >= attempts:
                raise
            await asyncio.sleep(backoff ** (attempt - 1))
