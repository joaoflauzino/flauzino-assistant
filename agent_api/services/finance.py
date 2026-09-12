import time
from typing import List

import httpx

from agent_api.core.decorators import handle_finance_errors
from agent_api.core.logger import get_logger
from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.limit import LimitDetails
from agent_api.schemas.spending import SpendingDetails
from agent_api.services.base import BaseHttpService
from agent_api.settings import settings

logger = get_logger(__name__)

_CACHE_TTL_SECONDS = 300  # 5 minutes

DEFAULT_CATEGORIES = [
    "alimentacao",
    "comer_fora",
    "farmacia",
    "mercado",
    "transporte",
    "moradia",
    "saude",
    "lazer",
    "educação",
    "compras",
    "vestuario",
    "viagem",
    "serviços",
    "crianças",
    "outros",
]

DEFAULT_PAYMENT_METHODS = ["itau", "nubank", "picpay", "xp", "c6", "pix"]


class FinanceService(BaseHttpService):
    _cached_categories: List[str] | None = None
    _categories_expiry: float = 0.0
    _cached_payment_methods: List[str] | None = None
    _payment_methods_expiry: float = 0.0

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(client)

    async def get_categories(self, use_cache: bool = True) -> List[str]:
        """Fetch valid categories with in-memory TTL caching."""
        now = time.monotonic()
        if (
            use_cache
            and FinanceService._cached_categories
            and now < FinanceService._categories_expiry
        ):
            return FinanceService._cached_categories

        url = f"{settings.FINANCE_SERVICE_URL}/categories/?size=100"
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                categories = [item["key"] for item in data.get("items", [])]
                if categories:
                    FinanceService._cached_categories = categories
                    FinanceService._categories_expiry = now + _CACHE_TTL_SECONDS
                    return categories
        except Exception as e:
            logger.warning(f"Failed to fetch categories from finance API: {e}")

        return FinanceService._cached_categories or DEFAULT_CATEGORIES

    async def get_payment_methods(self, use_cache: bool = True) -> List[str]:
        """Fetch valid payment methods with in-memory TTL caching."""
        now = time.monotonic()
        if (
            use_cache
            and FinanceService._cached_payment_methods
            and now < FinanceService._payment_methods_expiry
        ):
            return FinanceService._cached_payment_methods

        url = f"{settings.FINANCE_SERVICE_URL}/payment-methods/?size=100"
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                methods = [item["key"] for item in data.get("items", [])]
                if methods:
                    FinanceService._cached_payment_methods = methods
                    FinanceService._payment_methods_expiry = now + _CACHE_TTL_SECONDS
                    return methods
        except Exception as e:
            logger.warning(f"Failed to fetch payment methods from finance API: {e}")

        return FinanceService._cached_payment_methods or DEFAULT_PAYMENT_METHODS

    async def _post_to_finance_api(self, endpoint: str, payload: dict) -> dict:
        """Helper method to POST data to the finance API."""
        url = f"{settings.FINANCE_SERVICE_URL}/{endpoint}/"
        logger.info(f"Sending POST request to {url}")
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        logger.info("Finance API request successful")
        return response.json()

    @handle_finance_errors
    async def get_balances(self, categories: list[str] | None = None) -> list[dict]:
        """Fetch balances from the finance API with optional category filtering."""
        url = f"{settings.FINANCE_SERVICE_URL}/limits/balance"
        params = {}
        if categories:
            params["categories"] = ",".join(categories)

        logger.info(f"Fetching balances from {url}")
        response = await self.client.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return []

    @handle_finance_errors
    async def register(self, response: AssistantResponse) -> dict | None:
        """Register spending or limit based on the assistant response."""
        if response.spending_details:
            return await self.save_spent(response.spending_details)
        if response.limit_details:
            return await self.save_limit(response.limit_details)
        return None

    async def save_spent(self, details: SpendingDetails) -> dict:
        payload = {
            "category": details.categoria,
            "amount": details.valor,
            "item_bought": details.item_comprado,
            "payment_method": details.metodo_pagamento,
            "location": details.local_compra,
        }
        return await self._post_to_finance_api("spents", payload)

    async def save_limit(self, details: LimitDetails) -> dict:
        payload = {
            "category": details.category,
            "amount": details.value,
        }
        return await self._post_to_finance_api("limits", payload)
