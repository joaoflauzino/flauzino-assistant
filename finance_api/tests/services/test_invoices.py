import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from finance_api.services.invoices import compute_real_date, InvoiceService


def test_compute_real_date_weekend():
    # 25/10/2026 is a Sunday. It should shift to Monday, 26/10/2026.
    result = compute_real_date("2026-10", 25)
    assert result == date(2026, 10, 26)


def test_compute_real_date_holiday():
    # 01/11/2026 is Sunday. 02/11/2026 is a holiday (Finados).
    # So it should skip Sunday, skip Monday, and land on Tuesday 03/11/2026.
    result = compute_real_date("2026-11", 1)
    assert result == date(2026, 11, 3)


@pytest.mark.asyncio
async def test_get_invoice_dates():
    repo = AsyncMock()
    pm_repo = AsyncMock()
    service = InvoiceService(repo, pm_repo)

    pm = MagicMock()
    pm.is_credit_card = True
    pm.closing_day = 25
    pm.key = "nubank"

    repo.get_by_payment_method_and_month.return_value = None

    # Oct 25 2026 is Sunday, shifts to Oct 26.
    # Sep 25 2026 is Friday, stays Sep 25.
    # Start date = Sep 26, End date = Oct 26.
    start_d, end_d = await service.get_invoice_dates(pm, "2026-10")

    assert start_d == date(2026, 9, 26)
    assert end_d == date(2026, 10, 26)
