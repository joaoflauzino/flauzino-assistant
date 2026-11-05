from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.models.invoices import InvoiceStatus
from finance_api.services.invoices import (
    InvoiceService,
    compute_real_date,
    get_due_reference_month,
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
async def test_get_invoice_dates_rejects_non_credit_card_with_domain_error():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    pm = MagicMock()
    pm.is_credit_card = False
    pm.key = "itau_joao"

    with pytest.raises(ValidationError, match="itau_joao"):
        await service.get_invoice_dates(pm, "2026-10")

    repo.get_by_payment_method_and_month.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_billing_period_covers_purchases_of_the_civil_month():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    pm = MagicMock()
    pm.is_credit_card = True
    pm.closing_day = 25
    pm.due_day = 5
    pm.key = "nubank"
    repo.get_by_payment_method_and_month.return_value = None

    start_d, end_d = await service.get_billing_period(pm, "2026-10")

    # September invoice closes on 25/09 (Friday); October invoice closes on
    # 26/10 (25/10 is a Sunday). A purchase made on 10/10 belongs to this cycle.
    assert start_d == date(2026, 9, 26)
    assert end_d == date(2026, 10, 26)
    assert start_d <= date(2026, 10, 10) <= end_d


@pytest.mark.asyncio
async def test_get_billing_period_honors_manual_closing_overrides():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    pm = MagicMock()
    pm.is_credit_card = True
    pm.closing_day = 25
    pm.due_day = 5
    pm.key = "nubank"

    september_invoice = MagicMock(real_closing_date=date(2026, 9, 30))
    october_invoice = MagicMock(real_closing_date=date(2026, 10, 27))
    repo.get_by_payment_method_and_month.side_effect = [october_invoice, september_invoice]

    start_d, end_d = await service.get_billing_period(pm, "2026-10")

    assert start_d == date(2026, 10, 1)
    assert end_d == date(2026, 10, 27)


@pytest.mark.asyncio
async def test_get_billing_period_falls_back_to_civil_month_when_overrides_overlap():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    pm = MagicMock()
    pm.is_credit_card = True
    pm.closing_day = 5
    pm.due_day = 15
    pm.key = "nubank"

    september_invoice = MagicMock(real_closing_date=date(2026, 10, 10))
    october_invoice = MagicMock(real_closing_date=date(2026, 10, 5))
    repo.get_by_payment_method_and_month.side_effect = [october_invoice, september_invoice]

    start_d, end_d = await service.get_billing_period(pm, "2026-10")

    assert start_d == date(2026, 10, 1)
    assert end_d == date(2026, 10, 31)


@pytest.mark.asyncio
async def test_get_billing_period_rejects_non_credit_card():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    pm = MagicMock()
    pm.is_credit_card = False
    pm.key = "pix_joao"

    with pytest.raises(ValidationError):
        await service.get_billing_period(pm, "2026-10")


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


def make_credit_card_pm(
    pm_id: object | None = None,
    closing_day: int | None = 28,
    due_day: int | None = 5,
    key: str = "c6_joao",
) -> MagicMock:
    """Builds a credit card payment method double for invoice service tests."""
    pm = MagicMock()
    pm.id = uuid4() if pm_id is None else pm_id
    pm.key = key
    pm.is_credit_card = True
    pm.closing_day = closing_day
    pm.due_day = due_day
    return pm


def make_invoice_double(
    inv_id: object,
    *,
    status: InvoiceStatus = InvoiceStatus.OPEN,
    credit_card_id: object | None = None,
) -> MagicMock:
    """Builds an invoice double carrying every field required by InvoiceResponse."""
    invoice = MagicMock()
    invoice.id = inv_id
    invoice.payment_method_key = "c6_joao"
    invoice.credit_card_id = credit_card_id
    invoice.reference_month = "2026-09"
    invoice.real_closing_date = date(2026, 9, 28)
    invoice.real_due_date = date(2026, 10, 5)
    invoice.status = status
    invoice.created_at = datetime.now()
    return invoice


@pytest.mark.asyncio
async def test_update_invoice_dates_patches_only_closing_date():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    inv_id = uuid4()
    repo.get_by_payment_method_and_month.return_value = make_invoice_double(
        inv_id, credit_card_id=uuid4()
    )
    repo.update.return_value = make_invoice_double(inv_id, credit_card_id=uuid4())
    pm_repo.get_by_key.return_value = make_credit_card_pm()

    await service.update_invoice_dates("c6_joao", "2026-09", closing_date=date(2026, 9, 29))

    patch = repo.update.call_args[0][1]
    assert patch.model_dump(exclude_unset=True) == {"real_closing_date": date(2026, 9, 29)}


@pytest.mark.asyncio
async def test_update_invoice_dates_patches_only_due_date():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    inv_id = uuid4()
    repo.get_by_payment_method_and_month.return_value = make_invoice_double(
        inv_id, credit_card_id=uuid4()
    )
    repo.update.return_value = make_invoice_double(inv_id, credit_card_id=uuid4())
    pm_repo.get_by_key.return_value = make_credit_card_pm()

    await service.update_invoice_dates("c6_joao", "2026-09", due_date=date(2026, 10, 10))

    patch = repo.update.call_args[0][1]
    assert patch.model_dump(exclude_unset=True) == {"real_due_date": date(2026, 10, 10)}


@pytest.mark.asyncio
async def test_update_invoice_dates_links_missing_credit_card_id():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    inv_id = uuid4()
    card_id = uuid4()
    repo.get_by_payment_method_and_month.return_value = make_invoice_double(
        inv_id, credit_card_id=None
    )
    repo.update.return_value = make_invoice_double(inv_id, credit_card_id=card_id)
    pm_repo.get_by_key.return_value = make_credit_card_pm(pm_id=card_id)

    await service.update_invoice_dates("c6_joao", "2026-09", status=InvoiceStatus.PAID)

    patch = repo.update.call_args[0][1]
    assert patch.model_dump(exclude_unset=True) == {
        "status": InvoiceStatus.PAID,
        "credit_card_id": card_id,
    }


@pytest.mark.asyncio
async def test_update_invoice_dates_creates_invoice_with_default_days():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    card_id = uuid4()
    pm_repo.get_by_key.return_value = make_credit_card_pm(
        pm_id=card_id, closing_day=None, due_day=None
    )
    repo.get_by_payment_method_and_month.return_value = None
    created_inv = make_invoice_double(uuid4(), credit_card_id=card_id)
    created_inv.real_closing_date = date(2026, 9, 30)
    repo.create.return_value = created_inv

    result = await service.update_invoice_dates(
        "c6_joao", "2026-09", closing_date=date(2026, 9, 30)
    )

    created_payload = repo.create.call_args[0][0]
    assert created_payload.credit_card_id == card_id
    assert created_payload.real_closing_date == date(2026, 9, 30)
    assert created_payload.status == InvoiceStatus.OPEN
    assert result.real_closing_date == date(2026, 9, 30)


@pytest.mark.asyncio
async def test_update_invoice_dates_rejects_unknown_payment_method():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)
    pm_repo.get_by_key.return_value = None

    with pytest.raises(EntityNotFoundError, match="não encontrado"):
        await service.update_invoice_dates("cartao_fantasma", "2026-09")

    repo.update.assert_not_awaited()
    repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_invoice_dates_rejects_non_credit_card():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    pm = make_credit_card_pm(key="pix_joao")
    pm.is_credit_card = False
    pm_repo.get_by_key.return_value = pm

    with pytest.raises(EntityNotFoundError, match="não encontrado"):
        await service.update_invoice_dates("pix_joao", "2026-09")

    repo.update.assert_not_awaited()
    repo.create.assert_not_awaited()
