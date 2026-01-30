import httpx

from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.limit import LimitDetails
from agent_api.schemas.spending import SpendingDetails
from agent_api.settings import settings
from agent_api.core.decorators import handle_finance_errors


class FinanceService:
    def __init__(
        self,
        agent_response: AssistantResponse,
        client: httpx.AsyncClient,
    ):
        self.client = client
        self.agent_response = agent_response

    async def _post_to_finance_api(self, endpoint: str, payload: dict):
        """Helper method to POST data to the finance API."""
        url = f"{settings.API_BASE_URL}/{endpoint}/"
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    @handle_finance_errors
    async def register(self):
        if self.agent_response.spending_details:
            return await self.save_spent(self.agent_response.spending_details)
        if self.agent_response.limit_details:
            return await self.save_limit(self.agent_response.limit_details)

    async def save_spent(self, details: SpendingDetails):
        payload = {
            "category": details.categoria.value,
            "amount": details.valor,
            "payment_method": details.metodo_pagamento,
            "payment_owner": details.proprietário,
            "location": details.local_compra,
        }
        return await self._post_to_finance_api("spents", payload)

    async def save_limit(self, details: LimitDetails):
        payload = {
            "category": details.category.value,
            "amount": details.value,
        }
        return await self._post_to_finance_api("limits", payload)
