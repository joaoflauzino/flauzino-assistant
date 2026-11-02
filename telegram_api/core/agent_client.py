"""HTTP calls to agent_api: chat replies, receipt OCR and audio transcription."""

import time
from typing import Any

from telegram_api.core.http_client import get_http_client, get_request_headers, post_with_retry
from telegram_api.core.logger import get_logger
from telegram_api.settings import settings

logger = get_logger(__name__)


async def send_message_to_agent(message: str, session_id: str | None = None) -> dict[str, Any]:
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

    payload = {"message": message, "platform": "telegram"}
    if session_id:
        payload["session_id"] = session_id

    logger.info(f"Sending message to agent_api: {url}")
    client = get_http_client()
    start_time = time.perf_counter()

    response = await post_with_retry(
        lambda: client.post(url, json=payload, headers=get_request_headers())
    )

    elapsed = time.perf_counter() - start_time
    logger.info(f"Received response from agent_api in {elapsed:.2f}s")
    return response.json()


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
    data = {"platform": "telegram"}
    if session_id:
        data["session_id"] = session_id

    client = get_http_client()
    start_time = time.perf_counter()

    response = await post_with_retry(
        lambda: client.post(url, files=files, data=data, headers=get_request_headers())
    )

    elapsed = time.perf_counter() - start_time
    logger.info(f"Received OCR response from agent_api in {elapsed:.2f}s")
    return response.json()


async def send_audio_to_agent(
    file_content: bytes, filename: str, content_type: str, session_id: str | None = None
) -> dict[str, Any]:
    """Send an audio file to agent_api's /audio/process-audio endpoint.

    Args:
        file_content: The audio file bytes
        filename: The original filename or a generic one
        content_type: MIME type of the audio
        session_id: Optional session ID to continue a conversation

    Returns:
        The response from agent_api containing extracted text response and session info

    Raises:
        httpx.HTTPError: If the request fails
    """
    url = f"{settings.AGENT_API_URL}/audio/process-audio"

    logger.info(f"Sending audio to agent_api: {url}")

    files = {"file": (filename, file_content, content_type)}
    data = {"platform": "telegram"}
    if session_id:
        data["session_id"] = session_id

    client = get_http_client()
    start_time = time.perf_counter()

    response = await post_with_retry(
        lambda: client.post(url, files=files, data=data, headers=get_request_headers())
    )

    elapsed = time.perf_counter() - start_time
    logger.info(f"Received audio response from agent_api in {elapsed:.2f}s")
    return response.json()
