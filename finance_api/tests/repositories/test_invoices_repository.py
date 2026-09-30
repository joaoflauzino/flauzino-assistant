from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.models.invoices import Invoice, InvoiceStatus
from finance_api.repositories.invoices import InvoiceRepository
from finance_api.schemas.invoices import InvoiceCreate, InvoiceUpdate


@pytest.fixture
def mock_db_session():
    """Fixture for a mocked async database session."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    session.add = MagicMock()
    return session


async def test_create_invoice_success(mock_db_session):
    repo = InvoiceRepository(mock_db_session)
    invoice_data = InvoiceCreate(
        payment_method_key="c6_joao",
        reference_month="2026-09",
        real_closing_date=date(2026, 9, 28),
        real_due_date=date(2026, 10, 5),
        status=InvoiceStatus.OPEN,
    )

    created = await repo.create(invoice_data)

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()

    assert created.payment_method_key == "c6_joao"
    assert created.reference_month == "2026-09"
    assert created.status == InvoiceStatus.OPEN
    # Ensure status column is mapped as String/VARCHAR compatible Enum (native_enum=False)
    status_column = Invoice.__table__.columns["status"]
    assert status_column.type.native_enum is False


async def test_update_invoice_success(mock_db_session):
    repo = InvoiceRepository(mock_db_session)
    inv_id = uuid4()
    mock_invoice = Invoice(
        id=inv_id,
        payment_method_key="c6_joao",
        reference_month="2026-09",
        real_closing_date=date(2026, 9, 28),
        real_due_date=date(2026, 10, 5),
        status=InvoiceStatus.OPEN,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_invoice
    mock_db_session.execute.return_value = mock_result

    updated = await repo.update(
        inv_id,
        InvoiceUpdate(real_closing_date=date(2026, 9, 30)),
    )

    mock_db_session.commit.assert_awaited_once()
    assert updated is not None
    assert updated.payment_method_key == "c6_joao"
