import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from finance_api.models.invoices import InvoiceStatus
from finance_api.services.invoices import (
    compute_real_date,
    get_due_reference_month,
    InvoiceService,
)


def test_compute_real_date_weekend():
    # 25/10/2026 is a Sunday. It should shift to Monday, 26/10/2026.
    result = compute_real_date("2026-10", 25)
    assert result == date(2026, 10, 26)


def test_compute_real_date_holiday():
    # 01/11/2026 is Sunday. 02/11/2026 is a holiday (Finados).
    # So it should skip Sunday, skip Monday, and land on Tuesday 03/11/2026.
    result = compute_real_date("2026-11", 1)
    assert result == date(2026, 11, 3)


def test_get_due_reference_month():
    # When due_day <= closing_day (e.g. closes on the 28th, due on 5th), shift to next month
    assert get_due_reference_month("2026-09", closing_day=28, due_day=5) == "2026-10"
    assert get_due_reference_month("2026-12", closing_day=28, due_day=5) == "2027-01"

    # When due_day > closing_day (e.g. closes on 10th, due on 20th), same month
    assert get_due_reference_month("2026-09", closing_day=10, due_day=20) == "2026-09"


@pytest.mark.asyncio
async def test_get_invoice_dates():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    pm = MagicMock()
    pm.is_credit_card = True
    pm.closing_day = 25
    pm.due_day = 5
    pm.key = "nubank"

    repo.get_by_payment_method_and_month.return_value = None

    # Oct 25 2026 is Sunday, shifts to Monday Oct 26.
    # due_day (5) <= closing_day (25), so due_date is in next month: Nov 05, 2026.
    closing_d, due_d = await service.get_invoice_dates(pm, "2026-10")

    assert closing_d == date(2026, 10, 26)
    assert due_d == date(2026, 11, 5)


@pytest.mark.asyncio
async def test_list_previews_due_date_rollover():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    pm = MagicMock()
    pm.is_credit_card = True
    pm.closing_day = 28
    pm.due_day = 5
    pm.key = "c6_joao"

    pm_repo.list_credit_cards.return_value = [pm]
    repo.list_by_month.return_value = []

    # For September 2026: closes 28/09/2026 (Monday), due 05/10/2026 (Monday)
    previews = await service.list_previews("2026-09")
    assert len(previews) == 1
    assert previews[0].payment_method_key == "c6_joao"
    assert previews[0].real_closing_date == date(2026, 9, 28)
    assert previews[0].real_due_date == date(2026, 10, 5)


@pytest.mark.asyncio
async def test_update_closing_date_new_invoice_rollover():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    repo.get_by_payment_method_and_month.return_value = None

    pm = MagicMock()
    pm.is_credit_card = True
    pm.closing_day = 28
    pm.due_day = 5
    pm.key = "c6_joao"
    pm_repo.get_by_key.return_value = pm

    created_inv = MagicMock()
    created_inv.id = uuid4()
    created_inv.status = InvoiceStatus.OPEN
    created_inv.created_at = datetime.now()
    created_inv.payment_method_key = "c6_joao"
    created_inv.reference_month = "2026-09"
    created_inv.real_closing_date = date(2026, 9, 30)
    created_inv.real_due_date = date(2026, 10, 5)
    repo.create.return_value = created_inv

    await service.update_closing_date("c6_joao", "2026-09", date(2026, 9, 30))

    repo.create.assert_awaited_once()
    create_args = repo.create.call_args[0][0]
    assert create_args.real_closing_date == date(2026, 9, 30)
    assert create_args.real_due_date == date(2026, 10, 5)


@pytest.mark.asyncio
async def test_update_invoice_dates_both():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    existing_inv = MagicMock()
    inv_id = uuid4()
    existing_inv.id = inv_id
    existing_inv.payment_method_key = "c6_joao"
    existing_inv.reference_month = "2026-09"
    existing_inv.status = InvoiceStatus.OPEN

    repo.get_by_payment_method_and_month.return_value = existing_inv

    updated_inv = MagicMock()
    updated_inv.id = inv_id
    updated_inv.payment_method_key = "c6_joao"
    updated_inv.reference_month = "2026-09"
    updated_inv.real_closing_date = date(2026, 9, 29)
    updated_inv.real_due_date = date(2026, 10, 10)
    updated_inv.status = InvoiceStatus.CLOSED
    updated_inv.created_at = datetime.now()
    repo.update.return_value = updated_inv

    result = await service.update_invoice_dates(
        "c6_joao",
        "2026-09",
        closing_date=date(2026, 9, 29),
        due_date=date(2026, 10, 10),
        status=InvoiceStatus.CLOSED,
    )

    repo.update.assert_awaited_once()
    assert result.real_closing_date == date(2026, 9, 29)
    assert result.real_due_date == date(2026, 10, 10)
    assert result.status == InvoiceStatus.CLOSED


@pytest.mark.asyncio
async def test_mark_as_paid_existing_invoice():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    existing_inv = MagicMock()
    inv_id = uuid4()
    existing_inv.id = inv_id
    existing_inv.payment_method_key = "c6_joao"
    existing_inv.reference_month = "2026-09"
    existing_inv.real_closing_date = date(2026, 9, 28)
    existing_inv.real_due_date = date(2026, 10, 5)
    existing_inv.status = InvoiceStatus.OPEN
    repo.get_by_payment_method_and_month.return_value = existing_inv

    paid_inv = MagicMock()
    paid_inv.id = inv_id
    paid_inv.payment_method_key = "c6_joao"
    paid_inv.reference_month = "2026-09"
    paid_inv.real_closing_date = date(2026, 9, 28)
    paid_inv.real_due_date = date(2026, 10, 5)
    paid_inv.status = InvoiceStatus.PAID
    paid_inv.created_at = datetime.now()
    repo.update.return_value = paid_inv

    result = await service.mark_as_paid("c6_joao", "2026-09")

    repo.update.assert_awaited_once()
    assert result.status == InvoiceStatus.PAID


@pytest.mark.asyncio
async def test_reopen_invoice():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    existing_inv = MagicMock()
    inv_id = uuid4()
    existing_inv.id = inv_id
    existing_inv.payment_method_key = "c6_joao"
    existing_inv.reference_month = "2026-09"
    existing_inv.real_closing_date = date(2026, 9, 28)
    existing_inv.real_due_date = date(2026, 10, 5)
    existing_inv.status = InvoiceStatus.PAID
    repo.get_by_payment_method_and_month.return_value = existing_inv

    reopened_inv = MagicMock()
    reopened_inv.id = inv_id
    reopened_inv.payment_method_key = "c6_joao"
    reopened_inv.reference_month = "2026-09"
    reopened_inv.real_closing_date = date(2026, 9, 28)
    reopened_inv.real_due_date = date(2026, 10, 5)
    reopened_inv.status = InvoiceStatus.OPEN
    reopened_inv.created_at = datetime.now()
    repo.update.return_value = reopened_inv

    result = await service.reopen_invoice("c6_joao", "2026-09")

    repo.update.assert_awaited_once()
    assert result.status == InvoiceStatus.OPEN
