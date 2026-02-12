"""HTTP client for communicating with agent_api."""

import asyncio
import httpx
from typing import Any

from telegram_api.settings import settings
from telegram_api.core.logger import get_logger

logger = get_logger(__name__)

# Single persistent HTTP client - reused across all requests
_http_client: httpx.AsyncClient | None = None


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


async def send_message_to_agent(message: str, session_id: str) -> dict[str, Any]:
    """Send a text message to agent_api's /chat endpoint.

    Args:
        message: The user's message text
        session_id: The session ID (e.g., "telegram_123456789")

    Returns:
        The response from agent_api containing 'response', 'session_id', and 'history'

    Raises:
        httpx.HTTPError: If the request fails
    """
    url = f"{settings.AGENT_API_URL}/chat"
    payload = {
        "message": message,
        "session_id": session_id,
    }

    logger.info(f"Sending message to agent_api: {url}")
    client = get_http_client()

    for attempt in range(3):
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Received response from agent_api (attempt {attempt + 1})")
            return data
        except httpx.HTTPError as e:
            logger.warning(f"HTTP error on attempt {attempt + 1}: {e}")
            if attempt == 2:
                raise
            await asyncio.sleep(2**attempt)  # Exponential backoff


async def send_receipt_to_agent(
    file_content: bytes, filename: str, session_id: str | None = None
) -> dict[str, Any]:
    """Send a receipt image to agent_api's /ocr/process-receipt endpoint.

    Args:
        file_content: The image file bytes
        filename: The original filename
        session_id: Optional session ID to continue a conversation

    Returns:
        The response from agent_api containing OCR results and AI response

    Raises:
        httpx.HTTPError: If the request fails
    """
    url = f"{settings.AGENT_API_URL}/ocr/process-receipt"

    logger.info(f"Sending receipt to agent_api: {url}")

    files = {"file": (filename, file_content, "image/jpeg")}
    data = {}
    if session_id:
        data["session_id"] = session_id

    client = get_http_client()

    for attempt in range(3):
        try:
            response = await client.post(url, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Received OCR response from agent_api (attempt {attempt + 1})")
            return result
        except httpx.HTTPError as e:
            logger.warning(f"HTTP error on attempt {attempt + 1}: {e}")
            if attempt == 2:
                raise
            await asyncio.sleep(2**attempt)  # Exponential backoff
