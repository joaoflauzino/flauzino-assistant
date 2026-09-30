from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from finance_api.core.database import get_db
from finance_api.main import app
from finance_api.models.invoices import InvoiceStatus
from finance_api.models.payment_methods import PaymentMethod
from finance_api.routers.invoices import get_invoice_service

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_client():
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def test_list_invoices_router_integration(test_client):
    # Tests router with real InvoiceService and PaymentMethodRepository
    mock_db = AsyncMock()
    card = PaymentMethod(
        id=uuid4(),
        key="c6_joao",
        display_name="C6 João",
        is_credit_card=True,
        closing_day=28,
        due_day=5,
    )
    # 1st execute for list_credit_cards, 2nd for list_by_month
    mock_db.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[card])))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
    ]
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = await test_client.get("/invoices/2026-09")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["payment_method_key"] == "c6_joao"
        assert data[0]["real_closing_date"] == "2026-09-28"
        assert data[0]["real_due_date"] == "2026-10-05"
        assert data[0]["status"] == "OPEN"
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_update_invoice_dates_router(test_client):
    inv_id = uuid4()
    mock_service = MagicMock()
    mock_service.update_invoice_dates = AsyncMock(
        return_value=MagicMock(
            id=inv_id,
            payment_method_key="c6_joao",
            reference_month="2026-09",
            real_closing_date=date(2026, 9, 29),
            real_due_date=date(2026, 10, 10),
            status=InvoiceStatus.OPEN,
            created_at=datetime.now(),
        )
    )
    app.dependency_overrides[get_invoice_service] = lambda: mock_service

    try:
        response = await test_client.put(
            "/invoices/c6_joao/2026-09",
            json={
                "closing_date": "2026-09-29",
                "due_date": "2026-10-10",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["payment_method_key"] == "c6_joao"
        assert data["real_closing_date"] == "2026-09-29"
        assert data["real_due_date"] == "2026-10-10"
        mock_service.update_invoice_dates.assert_awaited_once_with(
            "c6_joao",
            "2026-09",
            closing_date=date(2026, 9, 29),
            due_date=date(2026, 10, 10),
            status=None,
        )
    finally:
        app.dependency_overrides.pop(get_invoice_service, None)


async def test_mark_invoice_as_paid_router(test_client):
    inv_id = uuid4()
    mock_service = MagicMock()
    mock_service.mark_as_paid = AsyncMock(
        return_value=MagicMock(
            id=inv_id,
            payment_method_key="c6_joao",
            reference_month="2026-09",
            real_closing_date=date(2026, 9, 28),
            real_due_date=date(2026, 10, 5),
            status=InvoiceStatus.PAID,
            created_at=datetime.now(),
        )
    )
    app.dependency_overrides[get_invoice_service] = lambda: mock_service

    try:
        response = await test_client.post(
            "/invoices/c6_joao/2026-09/pay",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PAID"
        mock_service.mark_as_paid.assert_awaited_once_with("c6_joao", "2026-09")
    finally:
        app.dependency_overrides.pop(get_invoice_service, None)


async def test_reopen_invoice_router(test_client):
    inv_id = uuid4()
    mock_service = MagicMock()
    mock_service.reopen_invoice = AsyncMock(
        return_value=MagicMock(
            id=inv_id,
            payment_method_key="c6_joao",
            reference_month="2026-09",
            real_closing_date=date(2026, 9, 28),
            real_due_date=date(2026, 10, 5),
            status=InvoiceStatus.OPEN,
            created_at=datetime.now(),
        )
    )
    app.dependency_overrides[get_invoice_service] = lambda: mock_service

    try:
        response = await test_client.post(
            "/invoices/c6_joao/2026-09/reopen",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OPEN"
        mock_service.reopen_invoice.assert_awaited_once_with("c6_joao", "2026-09")
    finally:
        app.dependency_overrides.pop(get_invoice_service, None)
