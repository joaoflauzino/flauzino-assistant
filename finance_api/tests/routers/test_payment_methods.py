from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from finance_api.core.database import get_db
from finance_api.core.service_dependencies import get_payment_method_service
from finance_api.main import app
from finance_api.models.accounts import Account
from finance_api.models.credit_cards import CreditCard
from finance_api.schemas.payment_methods import PaymentMethodResponse

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_client():
    """Fixture to create a test client for the FastAPI app."""
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def test_create_payment_method(test_client):
    """Test creating a new payment method."""
    app.dependency_overrides[get_db] = lambda: MagicMock()

    mock_service = AsyncMock()
    mock_service.create.return_value = PaymentMethodResponse(
        id=uuid4(),
        key="test_method",
        display_name="Test Method",
        created_at=datetime(2024, 1, 1),
    )
    app.dependency_overrides[get_payment_method_service] = lambda: mock_service

    payload = {"key": "test_method", "display_name": "Test Method"}
    response = await test_client.post("/payment-methods/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "test_method"
    mock_service.create.assert_awaited_once()

    app.dependency_overrides.clear()


async def test_list_payment_methods(test_client):
    """Test listing payment methods."""
    mock_service = AsyncMock()
    mock_service.list.return_value = ([], 0)
    app.dependency_overrides[get_payment_method_service] = lambda: mock_service

    response = await test_client.get("/payment-methods/")
    assert response.status_code == 200
    mock_service.list.assert_awaited_once()

    app.dependency_overrides.clear()


async def test_list_payment_methods_serializes_derived_sources(test_client):
    """Regression: payment methods derived from cards/accounts must expose created_at."""
    card = CreditCard(
        id=uuid4(),
        key="c6_card",
        name="C6 Carbon",
        account_id=uuid4(),
        closing_day=2,
        due_day=10,
        credit_limit=1000.0,
        created_at=datetime(2026, 1, 2, 3, 4, 5),
    )
    account = Account(
        id=uuid4(),
        key="c6_joao",
        name="C6 João",
        bank="c6",
        owner="joao",
        type="CHECKING",
        created_at=datetime(2026, 2, 3, 4, 5, 6),
    )

    def execute_result(items: list) -> MagicMock:
        result = MagicMock()
        result.scalars.return_value.all.return_value = items
        return result

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [execute_result([card]), execute_result([account])]
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = await test_client.get("/payment-methods/")
        assert response.status_code == 200
        data = response.json()
        assert [item["key"] for item in data["items"]] == ["c6_card", "c6_joao"]
        assert data["items"][0]["created_at"].startswith("2026-01-02")
        assert data["items"][1]["created_at"].startswith("2026-02-03")
        assert data["total"] == 2
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_get_payment_method(test_client):
    """Test getting a payment method by ID."""
    fake_id = uuid4()
    mock_service = AsyncMock()
    mock_service.get_by_id.return_value = PaymentMethodResponse(
        id=fake_id, key="get_test", display_name="Get Test", created_at=datetime(2024, 1, 1)
    )
    app.dependency_overrides[get_payment_method_service] = lambda: mock_service

    response = await test_client.get(f"/payment-methods/{fake_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(fake_id)

    app.dependency_overrides.clear()


async def test_update_payment_method(test_client):
    """Test updating a payment method."""
    fake_id = uuid4()
    mock_service = AsyncMock()
    mock_service.update.return_value = PaymentMethodResponse(
        id=fake_id, key="updated", display_name="Updated", created_at=datetime(2024, 1, 1)
    )
    app.dependency_overrides[get_payment_method_service] = lambda: mock_service

    payload = {"display_name": "Updated"}
    response = await test_client.put(f"/payment-methods/{fake_id}", json=payload)

    assert response.status_code == 200
    mock_service.update.assert_awaited_once()

    app.dependency_overrides.clear()


async def test_delete_payment_method(test_client):
    """Test deleting a payment method."""
    fake_id = uuid4()
    mock_service = AsyncMock()
    mock_service.delete.return_value = True
    app.dependency_overrides[get_payment_method_service] = lambda: mock_service

    response = await test_client.delete(f"/payment-methods/{fake_id}")
    assert response.status_code == 204
    mock_service.delete.assert_awaited_once()

    app.dependency_overrides.clear()
