from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from finance_api.main import app
from finance_api.routers.accounts import get_account_service
from finance_api.schemas.accounts import AccountResponse

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_client():
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def test_list_accounts(test_client):
    mock_service = AsyncMock()
    mock_service.list.return_value = ([], 0)
    app.dependency_overrides[get_account_service] = lambda: mock_service

    response = await test_client.get("/accounts/")
    assert response.status_code == 200
    mock_service.list.assert_awaited_once()

    app.dependency_overrides.clear()


async def test_create_account(test_client):
    mock_service = AsyncMock()
    fake_id = uuid4()
    mock_service.create.return_value = AccountResponse(
        id=fake_id,
        key="itau_joao",
        name="Itaú João",
        bank="itau",
        owner="joao",
        type="CHECKING",
        created_at=datetime(2026, 1, 1),
        credit_cards=[],
    )
    app.dependency_overrides[get_account_service] = lambda: mock_service

    payload = {
        "key": "itau_joao",
        "name": "Itaú João",
        "bank": "itau",
        "owner": "joao",
        "type": "CHECKING",
    }
    response = await test_client.post("/accounts/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "itau_joao"

    app.dependency_overrides.clear()


async def test_get_account(test_client):
    mock_service = AsyncMock()
    fake_id = uuid4()
    mock_service.get_by_id.return_value = AccountResponse(
        id=fake_id,
        key="itau_joao",
        name="Itaú João",
        bank="itau",
        owner="joao",
        type="CHECKING",
        created_at=datetime(2026, 1, 1),
        credit_cards=[],
    )
    app.dependency_overrides[get_account_service] = lambda: mock_service

    response = await test_client.get(f"/accounts/{fake_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(fake_id)

    app.dependency_overrides.clear()


async def test_delete_account(test_client):
    mock_service = AsyncMock()
    fake_id = uuid4()
    mock_service.delete.return_value = None
    app.dependency_overrides[get_account_service] = lambda: mock_service

    response = await test_client.delete(f"/accounts/{fake_id}")
    assert response.status_code == 204

    app.dependency_overrides.clear()
