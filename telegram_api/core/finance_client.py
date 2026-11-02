"""HTTP calls to finance_api and graph_api (valid keys, records, summaries and charts)."""

import base64
import time
from typing import Any

import httpx

from telegram_api.core.defaults import (
    DEFAULT_ACCOUNTS,
    DEFAULT_CATEGORIES,
    DEFAULT_CREDIT_CARDS,
    DEFAULT_INCOME_CATEGORIES,
    DEFAULT_OWNERS,
    DEFAULT_PAYMENT_METHODS,
)
from telegram_api.core.http_client import get_http_client, get_request_headers
from telegram_api.core.logger import get_logger
from telegram_api.settings import settings

logger = get_logger(__name__)


async def fetch_keys(path: str, fallback: list[str], label: str) -> list[str]:
    """Fetches a list of keys from finance_api, falling back to the static defaults."""
    try:
        client = get_http_client()
        response = await client.get(f"{settings.FINANCE_SERVICE_URL}{path}")
        if response.status_code == 200:
            return [item["key"] for item in response.json().get("items", [])]
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
        logger.warning(f"Failed to fetch {label}: {error}")
    return fallback


async def get_valid_categories() -> list[str]:
    """Fetch valid categories from finance API."""
    return await fetch_keys("/categories/?size=100", DEFAULT_CATEGORIES, "categories")


async def get_valid_income_categories() -> list[str]:
    """Fetch valid income categories from finance API."""
    return await fetch_keys(
        "/income-categories/?size=100", DEFAULT_INCOME_CATEGORIES, "income categories"
    )


async def get_valid_payment_methods() -> list[str]:
    """Fetch valid payment methods from finance API."""
    return await fetch_keys(
        "/payment-methods/?size=100", DEFAULT_PAYMENT_METHODS, "payment methods"
    )


async def get_valid_accounts() -> list[str]:
    """Fetch valid accounts from finance API."""
    return await fetch_keys("/accounts/?size=100", DEFAULT_ACCOUNTS, "accounts")


async def get_valid_credit_cards() -> list[str]:
    """Fetch valid credit cards from finance API."""
    return await fetch_keys("/credit-cards/?size=100", DEFAULT_CREDIT_CARDS, "credit cards")


async def get_valid_owners() -> list[str]:
    """Fetch valid payment owners from finance API."""
    return await fetch_keys("/payment-owners/?size=100", DEFAULT_OWNERS, "payment owners")


async def save_spent(details: dict[str, Any]) -> dict[str, Any]:
    """Save a spent directly to finance API.

    Args:
        details: dict with category, amount, item_bought, payment_method, payment_owner, location
    """
    url = f"{settings.FINANCE_SERVICE_URL}/spents/"
    logger.info(f"Sending POST request to {url}")
    client = get_http_client()

    response = await client.post(url, json=details, headers=get_request_headers())
    response.raise_for_status()
    logger.info("Finance API request successful")
    return response.json()


async def save_income(details: dict[str, Any]) -> dict[str, Any]:
    """Save an income directly to finance API.

    Args:
        details: dict with description, amount, category, payment_method
    """
    url = f"{settings.FINANCE_SERVICE_URL}/incomes/"
    logger.info(f"Sending POST request to {url}")
    client = get_http_client()

    response = await client.post(url, json=details, headers=get_request_headers())
    response.raise_for_status()
    logger.info("Finance API request successful (income)")
    return response.json()


async def save_subscription(details: dict[str, Any]) -> dict[str, Any]:
    """Save a subscription directly to finance API.

    Args:
        details: dict with name, category, amount, payment_method, payment_owner
    """
    url = f"{settings.FINANCE_SERVICE_URL}/subscriptions/"
    logger.info(f"Sending POST request to {url}")
    client = get_http_client()

    response = await client.post(url, json=details, headers=get_request_headers())
    response.raise_for_status()
    logger.info("Finance API request successful (subscription)")
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

    response = await client.get(url, params=params, headers=get_request_headers())
    if response.status_code == 200:
        return response.json()
    logger.warning(
        f"Failed to fetch monthly balance summary: {response.status_code} - {response.text}"
    )
    return None


async def fetch_balances(client: httpx.AsyncClient) -> list[dict[str, Any]] | None:
    """Fetches the month's balance limits; ``None`` means none are registered (404)."""
    finance_url = f"{settings.FINANCE_SERVICE_URL}/limits/balance"
    response = await client.get(finance_url, headers=get_request_headers())
    if response.status_code == 404:
        logger.info("No balance limits registered for this month (404)")
        return None

    response.raise_for_status()
    return response.json()


def filter_balances(
    balances: list[dict[str, Any]],
    categories: set[str] | list[str] | None,
) -> list[dict[str, Any]]:
    """Keeps only the requested categories, falling back to every balance when none match."""
    if not categories:
        return balances

    selected = {str(category).lower().strip() for category in categories}
    filtered = [
        balance
        for balance in balances
        if balance.get("category", "").lower() in selected
        or balance.get("category_display_name", "").lower() in selected
    ]
    return filtered or balances


async def render_balance_graph(
    client: httpx.AsyncClient,
    balances: list[dict[str, Any]],
    mode: str,
) -> bytes | None:
    """Renders the bar chart in graph_api and returns the decoded image bytes."""
    graph_url = f"{settings.GRAPH_SERVICE_URL}/graphs/bar"
    response = await client.post(
        graph_url,
        json={"balances": balances, "mode": mode},
        headers=get_request_headers(),
    )
    response.raise_for_status()
    data = response.json()

    if "image_base64" in data:
        return base64.b64decode(data["image_base64"])
    return None


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

    balances = await fetch_balances(client)
    if balances is None:
        return None
    if not balances:
        logger.info("No balance data available.")
        return None

    image = await render_balance_graph(client, filter_balances(balances, categories), mode)

    elapsed = time.perf_counter() - start_time
    logger.info(f"Balance graph generated in {elapsed:.2f}s")
    return image
