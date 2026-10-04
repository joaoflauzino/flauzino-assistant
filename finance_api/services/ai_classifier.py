from typing import Any
import httpx

from finance_api.core.http_client import get_http_client
from finance_api.core.logger import get_logger
from finance_api.settings import settings

logger = get_logger(__name__)


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

        payload = {
            "transactions": transactions,
            "expense_categories": expense_categories,
            "income_categories": income_categories,
        }

        url = f"{self.base_url}/classify/transactions"
        try:
            logger.info(f"Calling AI classifier at {url} for {len(transactions)} items")
            response = await self.client.post(url, json=payload, timeout=timeout_seconds)
            if response.status_code == 200:
                data = response.json()
                results: dict[str, tuple[str | None, float | None]] = {}
                for item in data.get("suggestions", []):
                    tx_id = str(item.get("id"))
                    cat = item.get("category")
                    conf = item.get("confidence")
                    results[tx_id] = (cat, float(conf) if conf is not None else None)
                return results, True
            else:
                logger.warning(
                    f"AI classifier returned status {response.status_code}: {response.text[:200]}"
                )
                return {}, False
        except Exception as e:
            logger.warning(f"AI classifier request failed ({e}); falling back to rules/memory")
            return {}, False
