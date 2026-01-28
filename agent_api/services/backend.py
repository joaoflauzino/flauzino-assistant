import httpx

from agent_api.schemas.limit import LimitDetails
from agent_api.schemas.spending import SpendingDetails
from config.settings import settings


async def save_spent(details: SpendingDetails):
    async with httpx.AsyncClient() as client:
        payload = {
            "category": details.categoria.value,
            "amount": details.valor,
            "payment_method": details.metodo_pagamento,
            "payment_owner": details.proprietário,
            "location": details.local_compra,
        }
        response = await client.post(f"{settings.API_BASE_URL}/spents", json=payload)
        response.raise_for_status()
        return response.json()


async def save_limit(details: LimitDetails):
    async with httpx.AsyncClient() as client:
        payload = {
            "category": details.category.value,
            "amount": details.value,
        }
        response = await client.post(f"{settings.API_BASE_URL}/limits", json=payload)
        response.raise_for_status()
        return response.json()
