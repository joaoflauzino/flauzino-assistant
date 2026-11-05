from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from finance_api.core.service_dependencies import get_spent_service
from finance_api.main import app
from finance_api.services.spents import SpentService
from finance_api.tests.fakes.fake_payment_resolver import FakePaymentResolver

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_category_repo():
    """Fixture for a category repository double."""
    repo = AsyncMock()
    repo.get_by_key.return_value = MagicMock(key="mercado")
    return repo


@pytest.fixture
def mock_payment_method_repo():
    """Fixture for a payment method repository double."""
    repo = AsyncMock()
    repo.get_by_key.return_value = MagicMock(key="itau", is_credit_card=False)
    return repo


@pytest.fixture
def mock_invoice_service():
    """Fixture for an invoice service double."""
    return AsyncMock()


@pytest.fixture
def mock_spent_repository():
    """Fixture for a mocked SpentRepository."""
    return AsyncMock()


@pytest.fixture(autouse=True)
def spent_service_override(
    mock_spent_repository,
    mock_category_repo,
    mock_payment_method_repo,
    mock_invoice_service,
):
    """Injects a real SpentService backed by repository doubles."""
    app.dependency_overrides[get_spent_service] = lambda: SpentService(
        repo=mock_spent_repository,
        category_repo=mock_category_repo,
        pm_repo=mock_payment_method_repo,
        payment_resolver=FakePaymentResolver(),
        inv_service=mock_invoice_service,
    )
    yield
    app.dependency_overrides.pop(get_spent_service, None)


@pytest.fixture
async def test_client():
    """Fixture to create a test client for the FastAPI app."""
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def test_create_spent_success(test_client, mock_spent_repository):
    """
    Test successful creation of a spent record.
    """
    payload = {
        "category": "mercado",
        "amount": 150.50,
        "item_bought": "item1",
        "payment_method": "itau",
        "payment_owner": "joao_lucas",
        "location": "Supermarket",
    }
    fake_id = uuid4()
    mock_spent_repository.create.return_value = MagicMock(
        id=fake_id,
        created_at="2023-01-01T12:00:00",
        **payload,
        is_installment=False,
        installment_id=None,
        current_installment=None,
        total_installments=None,
    )

    response = await test_client.post("/spents/", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == str(fake_id)
    assert response_data["category"] == payload["category"]
    assert response_data["amount"] == payload["amount"]
    mock_spent_repository.create.assert_awaited_once()


async def test_list_spents_success(test_client, mock_spent_repository):
    """
    Test successful listing of spent records.
    """
    id1 = uuid4()
    id2 = uuid4()

    mock_return_data = [
        MagicMock(
            id=id1,
            category="mercado",
            amount=100.0,
            item_bought="item1",
            created_at="2023-01-01T12:00:00",
            payment_method="itau",
            payment_owner="joao_lucas",
            location="A",
            is_installment=False,
            installment_id=None,
            current_installment=None,
            total_installments=None,
        ),
        MagicMock(
            id=id2,
            category="lazer",
            amount=50.0,
            item_bought="item2",
            created_at="2023-01-02T12:00:00",
            payment_method="c6",
            payment_owner="lailla",
            location="B",
            is_installment=False,
            installment_id=None,
            current_installment=None,
            total_installments=None,
        ),
    ]
    mock_spent_repository.list.return_value = (mock_return_data, 2)

    # Default page=1, size=10 -> skip=0, limit=10
    response = await test_client.get("/spents/")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["items"]) == 2
    assert response_data["items"][0]["id"] == str(id1)
    assert response_data["items"][1]["id"] == str(id2)
    assert response_data["total"] == 2
    assert response_data["page"] == 1
    assert response_data["size"] == 10
    assert response_data["pages"] == 1
    # Repository list now has 4 params: skip, limit, start_date, end_date
    mock_spent_repository.list.assert_awaited_once_with(0, 10, None, None)


async def test_get_spent_by_id_success(test_client, mock_spent_repository):
    """Test successful retrieval of a spent record by ID."""
    fake_id = uuid4()
    mock_spent_repository.get_by_id.return_value = MagicMock(
        id=fake_id,
        category="mercado",
        amount=100.0,
        item_bought="item1",
        created_at="2023-01-01T12:00:00",
        payment_method="itau",
        payment_owner="joao_lucas",
        location="A",
        is_installment=False,
        installment_id=None,
        current_installment=None,
        total_installments=None,
    )

    response = await test_client.get(f"/spents/{fake_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(fake_id)
    mock_spent_repository.get_by_id.assert_awaited_once_with(fake_id)


async def test_get_spent_by_id_not_found(test_client, mock_spent_repository):
    """Test retrieval of non-existent spent record returns 404."""
    mock_spent_repository.get_by_id.return_value = None
    fake_id = uuid4()

    response = await test_client.get(f"/spents/{fake_id}")

    assert response.status_code == 404
    mock_spent_repository.get_by_id.assert_awaited_once_with(fake_id)


async def test_update_spent_success(test_client, mock_spent_repository):
    """Test successful update of a spent record."""
    fake_id = uuid4()
    mock_spent_repository.update.return_value = MagicMock(
        id=fake_id,
        category="lazer",
        amount=200.0,
        item_bought="item1",
        created_at="2023-01-01T12:00:00",
        payment_method="itau",
        payment_owner="joao_lucas",
        location="A",
        is_installment=False,
        installment_id=None,
        current_installment=None,
        total_installments=None,
    )

    payload = {"amount": 200.0, "category": "lazer"}

    response = await test_client.patch(f"/spents/{fake_id}", json=payload)

    assert response.status_code == 200
    assert response.json()["amount"] == 200.0
    mock_spent_repository.update.assert_awaited_once()


async def test_delete_spent_success(test_client, mock_spent_repository):
    """Test successful deletion of a spent record."""
    mock_spent_repository.delete.return_value = True
    fake_id = uuid4()

    response = await test_client.delete(f"/spents/{fake_id}")

    assert response.status_code == 204
    mock_spent_repository.delete.assert_awaited_once_with(fake_id)


async def test_create_spent_repository_error(test_client, mock_spent_repository):
    """
    Test handling of a 500 error when the repository fails.
    """
    mock_spent_repository.create.side_effect = Exception("Database connection failed")
    payload = {
        "category": "mercado",
        "amount": 150.50,
        "item_bought": "item1",
        "payment_method": "itau",
        "payment_owner": "joao_lucas",
        "location": "Supermarket",
    }

    response = await test_client.post("/spents/", json=payload)

    assert response.status_code == 500
    response_json = response.json()
    assert response_json["message"] == "Internal Server Error"
    assert "Database connection failed" in response_json["detail"]


async def test_list_spents_pagination(test_client, mock_spent_repository):
    """
    Test listing spent records with pagination.
    """
    id1 = uuid4()
    mock_spents = [
        MagicMock(
            id=id1,
            category="mercado",
            amount=100.0,
            item_bought="item1",
            created_at="2023-01-01T12:00:00",
            payment_method="itau",
            payment_owner="joao_lucas",
            location="A",
            is_installment=False,
            installment_id=None,
            current_installment=None,
            total_installments=None,
        ),
    ]
    # Simulate pagination returning only the first item, but total is 2
    mock_spent_repository.list.return_value = (mock_spents, 2)

    # Requesting page=1, size=1 -> skip=0, limit=1
    response = await test_client.get("/spents/?page=1&size=1")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["items"]) == 1
    assert response_data["items"][0]["id"] == str(id1)
    assert response_data["total"] == 2
    assert response_data["page"] == 1
    assert response_data["size"] == 1
    assert response_data["pages"] == 2
    # Repository list now has 4 params: skip, limit, start_date, end_date
    mock_spent_repository.list.assert_awaited_once_with(0, 1, None, None)


async def test_get_installments_summary_success(test_client, mock_spent_repository):
    """
    Test successful fetching of installments summary.
    """
    fake_id = uuid4()
    mock_spent_repository.get_installments_summary.return_value = [
        {
            "installment_id": fake_id,
            "category": "tecnologia",
            "item_bought": "Monitor",
            "amount": 100.0,
            "total_installments": 10,
            "passed_installments": 2,
        }
    ]

    response = await test_client.get("/spents/installments-summary")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["installment_id"] == str(fake_id)
    assert response_data[0]["category"] == "tecnologia"
    assert response_data[0]["item_bought"] == "Monitor"
    assert response_data[0]["passed_installments"] == 2
    mock_spent_repository.get_installments_summary.assert_awaited_once()


async def test_get_dashboard_invoices_mode_with_mixed_payment_methods(
    test_client,
    mock_spent_repository,
    mock_payment_method_repo,
    mock_invoice_service,
):
    card = MagicMock(key="nubank", is_credit_card=True)
    pix = MagicMock(key="pix_joao", is_credit_card=False)
    mock_payment_method_repo.list.return_value = ([card, pix], 2)

    mock_invoice_service.get_billing_period = AsyncMock(
        return_value=(date(2026, 8, 26), date(2026, 9, 25))
    )

    spent_card = MagicMock(
        id=uuid4(),
        category="mercado",
        amount=250.0,
        item_bought="Compras Mercado",
        created_at="2026-09-10T12:00:00",
        payment_method="nubank",
        payment_owner="joao",
        location="Mercado",
        is_installment=False,
        installment_id=None,
        current_installment=None,
        total_installments=None,
    )
    spent_pix = MagicMock(
        id=uuid4(),
        category="lazer",
        amount=80.0,
        item_bought="Ingresso Cinema",
        created_at="2026-09-15T12:00:00",
        payment_method="pix_joao",
        payment_owner="joao",
        location="Cinema",
        is_installment=False,
        installment_id=None,
        current_installment=None,
        total_installments=None,
    )

    mock_spent_repository.list_by_multiple_periods = AsyncMock(
        return_value=([spent_card, spent_pix], 2)
    )

    response = await test_client.get("/spents/dashboard?reference_month=2026-09&mode=INVOICES")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    mock_spent_repository.list_by_multiple_periods.assert_awaited_once()
    periods_arg = mock_spent_repository.list_by_multiple_periods.call_args[0][0]
    assert len(periods_arg) == 2
    assert periods_arg[0] == ("nubank", date(2026, 8, 26), date(2026, 9, 25))
    assert periods_arg[1] == ("pix_joao", date(2026, 9, 1), date(2026, 9, 30))
