from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from finance_api.main import app
from finance_api.routers.credit_cards import get_credit_card_service
from finance_api.schemas.credit_cards import CreditCardResponse

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_client():
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def test_list_credit_cards(test_client):
    mock_service = AsyncMock()
    mock_service.list.return_value = ([], 0)
    app.dependency_overrides[get_credit_card_service] = lambda: mock_service

    response = await test_client.get("/credit-cards/")
    assert response.status_code == 200
    mock_service.list.assert_awaited_once()

    app.dependency_overrides.clear()


async def test_create_credit_card(test_client):
    mock_service = AsyncMock()
    card_id = uuid4()
    acc_id = uuid4()
    mock_service.create.return_value = CreditCardResponse(
        id=card_id,
        key="itau_black",
        name="Itaú Black",
        account_id=acc_id,
        closing_day=2,
        due_day=10,
        credit_limit=10000.0,
        created_at=datetime(2026, 1, 1),
    )
    app.dependency_overrides[get_credit_card_service] = lambda: mock_service

    payload = {
        "key": "itau_black",
        "name": "Itaú Black",
        "account_id": str(acc_id),
        "closing_day": 2,
        "due_day": 10,
        "credit_limit": 10000.0,
    }
    response = await test_client.post("/credit-cards/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "itau_black"

    app.dependency_overrides.clear()


async def test_get_credit_card(test_client):
    mock_service = AsyncMock()
    card_id = uuid4()
    acc_id = uuid4()
    mock_service.get_by_id.return_value = CreditCardResponse(
        id=card_id,
        key="itau_black",
        name="Itaú Black",
        account_id=acc_id,
        closing_day=2,
        due_day=10,
        credit_limit=10000.0,
        created_at=datetime(2026, 1, 1),
    )
    app.dependency_overrides[get_credit_card_service] = lambda: mock_service

    response = await test_client.get(f"/credit-cards/{card_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(card_id)

    app.dependency_overrides.clear()


async def test_delete_credit_card(test_client):
    mock_service = AsyncMock()
    card_id = uuid4()
    mock_service.delete.return_value = None
    app.dependency_overrides[get_credit_card_service] = lambda: mock_service

    response = await test_client.delete(f"/credit-cards/{card_id}")
    assert response.status_code == 204

    app.dependency_overrides.clear()
