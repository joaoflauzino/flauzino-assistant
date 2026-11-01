from datetime import date
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from finance_api.models.payment_methods import PaymentMethod
from finance_api.models.spents import Spent
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.repositories.spents import SpentRepository
from finance_api.services.dashboard_strategies import (
    CivilMonthDashboardStrategy,
    InvoicesDashboardStrategy,
)
from finance_api.services.invoices import InvoiceService


@pytest.mark.asyncio
async def test_civil_month_dashboard_strategy():
    repo = AsyncMock(spec=SpentRepository)
    spent = Spent(id=uuid4(), amount=100.0, category="mercado")
    repo.list.return_value = ([spent], 1)

    strategy = CivilMonthDashboardStrategy(spent_repo=repo)
    items, total = await strategy.fetch_spents("2026-10", skip=0, size=10)

    assert total == 1
    assert items[0] == spent
    repo.list.assert_awaited_once_with(0, 10, date(2026, 10, 1), date(2026, 10, 31))


@pytest.mark.asyncio
async def test_invoices_dashboard_strategy():
    spent_repo = AsyncMock(spec=SpentRepository)
    inv_service = AsyncMock(spec=InvoiceService)
    pm_repo = AsyncMock(spec=PaymentMethodRepository)

    cc = PaymentMethod(id=uuid4(), key="c6_card", display_name="C6", is_credit_card=True)
    acc = PaymentMethod(id=uuid4(), key="itau", display_name="Itaú", is_credit_card=False)
    pm_repo.list.return_value = ([cc, acc], 2)

    inv_service.get_invoice_dates.return_value = (date(2026, 9, 28), date(2026, 10, 5))

    strategy = InvoicesDashboardStrategy(
        spent_repo=spent_repo,
        inv_service=inv_service,
        pm_repo=pm_repo,
    )
    periods = await strategy._resolve_invoice_periods("2026-10")

    assert len(periods) == 2
    assert periods[0] == ("c6_card", date(2026, 9, 28), date(2026, 10, 5))
    assert periods[1] == ("itau", date(2026, 10, 1), date(2026, 10, 31))
