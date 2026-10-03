"""HTTP client for communicating with agent_api."""

import asyncio
import base64
import time
from typing import Any

import httpx

from telegram_api.core.correlation import CORRELATION_HEADER, get_request_id, set_request_id
from telegram_api.core.logger import get_logger
from telegram_api.settings import settings

logger = get_logger(__name__)


def _get_headers() -> dict[str, str]:
    req_id = get_request_id() or set_request_id()
    return {CORRELATION_HEADER: req_id}


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

    for attempt in range(3):
        try:
            response = await client.post(url, json=payload, headers=_get_headers())
            response.raise_for_status()
            data = response.json()
            elapsed = time.perf_counter() - start_time
            logger.info(
                f"Received response from agent_api in {elapsed:.2f}s (attempt {attempt + 1})"
            )
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
    data = {"platform": "telegram"}
    if session_id:
        data["session_id"] = session_id

    client = get_http_client()
    start_time = time.perf_counter()

    for attempt in range(3):
        try:
            response = await client.post(url, files=files, data=data, headers=_get_headers())
            response.raise_for_status()
            result = response.json()
            elapsed = time.perf_counter() - start_time
            logger.info(
                f"Received OCR response from agent_api in {elapsed:.2f}s (attempt {attempt + 1})"
            )
            return result
        except httpx.HTTPError as e:
            logger.warning(f"HTTP error on attempt {attempt + 1}: {e}")
            if attempt == 2:
                raise
            await asyncio.sleep(2**attempt)  # Exponential backoff


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

    for attempt in range(3):
        try:
            response = await client.post(url, files=files, data=data, headers=_get_headers())
            response.raise_for_status()
            result = response.json()
            elapsed = time.perf_counter() - start_time
            logger.info(
                f"Received audio response from agent_api in {elapsed:.2f}s (attempt {attempt + 1})"
            )
            return result
        except httpx.HTTPError as e:
            logger.warning(f"HTTP error on attempt {attempt + 1}: {e}")
            if attempt == 2:
                raise
            await asyncio.sleep(2**attempt)  # Exponential backoff


async def get_valid_categories() -> list[str]:
    """Fetch valid categories from finance API."""
    try:
        client = get_http_client()
        response = await client.get(f"{settings.FINANCE_SERVICE_URL}/categories/?size=100")
        if response.status_code == 200:
            data = response.json()
            return [item["key"] for item in data.get("items", [])]
    except Exception as e:
        logger.warning(f"Failed to fetch categories: {e}")
    return [
        "alimentacao",
        "comer_fora",
        "farmacia",
        "mercado",
        "transporte",
        "moradia",
        "saude",
        "lazer",
        "educacao",
        "compras",
        "vestuario",
        "viagem",
        "servicos",
        "criancas",
        "outros",
    ]


async def get_valid_income_categories() -> list[str]:
    """Fetch valid income categories from finance API."""
    try:
        client = get_http_client()
        response = await client.get(f"{settings.FINANCE_SERVICE_URL}/income-categories/?size=100")
        if response.status_code == 200:
            data = response.json()
            return [item["key"] for item in data.get("items", [])]
    except Exception as e:
        logger.warning(f"Failed to fetch income categories: {e}")
    return ["salario", "pix", "premiacao", "investimentos", "reembolso", "outros"]


async def get_valid_payment_methods() -> list[str]:
    """Fetch valid payment methods from finance API."""
    try:
        client = get_http_client()
        response = await client.get(f"{settings.FINANCE_SERVICE_URL}/payment-methods/?size=100")
        if response.status_code == 200:
            data = response.json()
            return [item["key"] for item in data.get("items", [])]
    except Exception as e:
        logger.warning(f"Failed to fetch payment methods: {e}")
    return [
        "itau_card_joao",
        "nubank_card_joao",
        "nubank_card_lailla",
        "picpay_card_joao",
        "c6_card_joao",
        "itau_joao",
        "nubank_joao",
        "nubank_lailla",
        "picpay_joao",
        "c6_joao",
    ]


async def get_valid_accounts() -> list[str]:
    """Fetch valid accounts from finance API."""
    try:
        client = get_http_client()
        response = await client.get(f"{settings.FINANCE_SERVICE_URL}/accounts/?size=100")
        if response.status_code == 200:
            data = response.json()
            return [item["key"] for item in data.get("items", [])]
    except Exception as e:
        logger.warning(f"Failed to fetch accounts: {e}")
    return [
        "itau_joao",
        "nubank_joao",
        "nubank_lailla",
        "picpay_joao",
        "c6_joao",
    ]


async def get_valid_credit_cards() -> list[str]:
    """Fetch valid credit cards from finance API."""
    try:
        client = get_http_client()
        response = await client.get(f"{settings.FINANCE_SERVICE_URL}/credit-cards/?size=100")
        if response.status_code == 200:
            data = response.json()
            return [item["key"] for item in data.get("items", [])]
    except Exception as e:
        logger.warning(f"Failed to fetch credit cards: {e}")
    return [
        "itau_card_joao",
        "nubank_card_joao",
        "nubank_card_lailla",
        "picpay_card_joao",
        "c6_card_joao",
    ]


async def get_valid_owners() -> list[str]:
    """Fetch valid payment owners from finance API."""
    try:
        client = get_http_client()
        response = await client.get(f"{settings.FINANCE_SERVICE_URL}/payment-owners/?size=100")
        if response.status_code == 200:
            data = response.json()
            return [item["key"] for item in data.get("items", [])]
    except Exception as e:
        logger.warning(f"Failed to fetch payment owners: {e}")
    return ["joao_lucas", "lailla"]


async def save_spent(details: dict) -> dict[str, Any]:
    """Save a spent directly to finance API.

    Args:
        details: dict with category, amount, item_bought, payment_method, payment_owner, location
    """
    url = f"{settings.FINANCE_SERVICE_URL}/spents/"
    logger.info(f"Sending POST request to {url}")
    client = get_http_client()

    response = await client.post(url, json=details, headers=_get_headers())
    response.raise_for_status()
    logger.info("Finance API request successful")
    return response.json()


async def save_income(details: dict) -> dict[str, Any]:
    """Save an income directly to finance API.

    Args:
        details: dict with description, amount, category, payment_method
    """
    url = f"{settings.FINANCE_SERVICE_URL}/incomes/"
    logger.info(f"Sending POST request to {url}")
    client = get_http_client()

    response = await client.post(url, json=details, headers=_get_headers())
    response.raise_for_status()
    logger.info("Finance API request successful (income)")
    return response.json()


async def get_monthly_balance_summary(
    reference_month: str | None = None,
) -> dict[str, Any] | None:
    """Fetch monthly balance summary directly from finance API."""
    client = get_http_client()
    url = f"{settings.FINANCE_SERVICE_URL}/incomes/summary"
    params = {}
    if reference_month:
        params["reference_month"] = reference_month

    response = await client.get(url, params=params, headers=_get_headers())
    if response.status_code == 200:
        return response.json()
    logger.warning(
        f"Failed to fetch monthly balance summary: {response.status_code} - {response.text}"
    )
    return None


async def save_subscription(details: dict) -> dict[str, Any]:
    """Save a subscription directly to finance API.

    Args:
        details: dict with name, category, amount, payment_method, payment_owner
    """
    url = f"{settings.FINANCE_SERVICE_URL}/subscriptions/"
    logger.info(f"Sending POST request to {url}")
    client = get_http_client()

    response = await client.post(url, json=details, headers=_get_headers())
    response.raise_for_status()
    logger.info("Finance API request successful (subscription)")
    return response.json()


async def get_balance_graph(
    categories: set[str] | list[str] | None = None, mode: str = "saldo"
) -> bytes | None:
    """Fetch balances from finance_api, optionally filter by categories, and generate a graph from graph_api.

    Args:
        categories: Optional collection of category names to filter.
        mode: Balance mode ("saldo" or "limites").

    Returns:
        Image bytes (decoded) of the bar chart, or None if no balances are found or format is invalid.

    Raises:
        httpx.HTTPError: If the HTTP request to finance_api or graph_api fails (excluding 404 on finance).
    """
    client = get_http_client()
    start_time = time.perf_counter()

    finance_url = f"{settings.FINANCE_SERVICE_URL}/limits/balance"
    fin_resp = await client.get(finance_url, headers=_get_headers())
    if fin_resp.status_code == 404:
        logger.info("No balance limits registered for this month (404)")
        return None

    fin_resp.raise_for_status()
    balances = fin_resp.json()

    if not balances:
        logger.info("No balance data available.")
        return None

    if categories:
        selected_lower = {s.lower().strip() for s in categories}
        filtered_balances = [
            b
            for b in balances
            if b.get("category", "").lower() in selected_lower
            or b.get("category_display_name", "").lower() in selected_lower
        ] or balances
    else:
        filtered_balances = balances

    graph_url = f"{settings.GRAPH_SERVICE_URL}/graphs/bar"
    response = await client.post(
        graph_url,
        json={
            "balances": filtered_balances,
            "mode": mode,
        },
        headers=_get_headers(),
    )
    response.raise_for_status()
    data = response.json()

    elapsed = time.perf_counter() - start_time
    logger.info(f"Balance graph generated in {elapsed:.2f}s")

    if "image_base64" in data:
        return base64.b64decode(data["image_base64"])
    return None
