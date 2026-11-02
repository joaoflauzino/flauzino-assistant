from typing import Any

import httpx

from finance_api.core.http_client import get_http_client
from finance_api.core.logger import get_logger
from finance_api.settings import settings

logger = get_logger(__name__)

CLASSIFY_PATH = "/classify/transactions"
SUCCESS_STATUS = 200


def build_classify_payload(
    transactions: list[dict[str, Any]],
    expense_categories: list[dict[str, str]],
    income_categories: list[dict[str, str]],
) -> dict[str, Any]:
    """Builds the request body expected by the agent classification endpoint."""
    return {
        "transactions": transactions,
        "expense_categories": expense_categories,
        "income_categories": income_categories,
    }


def extract_suggestions(
    response_body: dict[str, Any],
) -> dict[str, tuple[str | None, float | None]]:
    """Maps the endpoint response into ``{tx_id_str: (category, confidence)}``."""
    suggestions: dict[str, tuple[str | None, float | None]] = {}
    for item in response_body.get("suggestions", []):
        confidence = item.get("confidence")
        suggestions[str(item.get("id"))] = (
            item.get("category"),
            float(confidence) if confidence is not None else None,
        )
    return suggestions


class AIClassifierClient:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or get_http_client()
        self.base_url = settings.AGENT_SERVICE_URL.rstrip("/")

    async def classify_batch(
        self,
        transactions: list[dict[str, Any]],
        expense_categories: list[dict[str, str]],
        income_categories: list[dict[str, str]],
        timeout_seconds: float = 25.0,
    ) -> tuple[dict[str, tuple[str | None, float | None]], bool]:
        """
        Envia lote para POST {AGENT_SERVICE_URL}/classify/transactions.
        Retorna:
          dict {tx_id_str: (category, confidence)}
          bool ai_used (True se o serviço respondeu com sucesso, False se falhou/timeout)
        """
        if not transactions:
            return {}, False

        payload = build_classify_payload(transactions, expense_categories, income_categories)
        response = await self._post(payload, timeout_seconds)
        if response is None:
            return {}, False

        body = self._decode(response)
        if body is None:
            return {}, False
        return extract_suggestions(body), True

    async def _post(
        self,
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> httpx.Response | None:
        url = f"{self.base_url}{CLASSIFY_PATH}"
        logger.info(f"Calling AI classifier at {url} for {len(payload['transactions'])} items")
        try:
            response = await self.client.post(url, json=payload, timeout=timeout_seconds)
        except httpx.HTTPError as error:
            logger.warning(f"AI classifier request failed ({error}); falling back to rules/memory")
            return None

        if response.status_code != SUCCESS_STATUS:
            logger.warning(
                f"AI classifier returned status {response.status_code}: {response.text[:200]}"
            )
            return None
        return response

    def _decode(self, response: httpx.Response) -> dict[str, Any] | None:
        try:
            return response.json()
        except ValueError as error:
            logger.warning(f"AI classifier returned invalid JSON ({error}); using fallback")
            return None
