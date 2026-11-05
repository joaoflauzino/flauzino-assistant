import asyncio
from datetime import date
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from finance_api.models.payment_methods import PaymentMethod
from finance_api.services.dashboard_protocols import DashboardPeriodStrategy
from finance_api.services.dashboard_strategies import (
    CivilMonthDashboardStrategy,
    InvoicesDashboardStrategy,
)
from finance_api.services.invoice_protocols import InvoicePeriodProviderProtocol
from finance_api.services.invoices import InvoiceService
from finance_api.services.payment_resolution import PaymentResolutionService
from finance_api.services.payment_resolution_protocols import (
    PaymentResolutionServiceProtocol,
)


def test_invoice_service_satisfies_period_provider_contract() -> None:
    service = InvoiceService(AsyncMock(), AsyncMock())

    provider: InvoicePeriodProviderProtocol = service

    assert provider is service


def test_payment_resolution_service_satisfies_resolver_contract() -> None:
    service = PaymentResolutionService(card_repo=AsyncMock(), account_repo=AsyncMock())

    resolver: PaymentResolutionServiceProtocol = service

    assert resolver is service


@pytest.mark.asyncio
async def test_dashboard_strategies_satisfy_period_strategy_contract() -> None:
    spent_repo = AsyncMock()
    spent_repo.list.return_value = ([], 0)
    spent_repo.list_by_multiple_periods.return_value = ([], 0)
    pm_repo = AsyncMock()
    pm_repo.list.return_value = ([], 0)

    strategies: list[DashboardPeriodStrategy] = [
        CivilMonthDashboardStrategy(spent_repo),
        InvoicesDashboardStrategy(spent_repo, AsyncMock(), pm_repo),
    ]

    for strategy in strategies:
        items, total = await strategy.fetch_spents("2026-10", 0, 10)
        assert items == []
        assert total == 0


def test_invoice_period_provider_accepts_structural_fake() -> None:
    payment_method = PaymentMethod(
        id=uuid4(),
        key="nubank",
        display_name="Nubank",
        is_credit_card=True,
    )

    class StructuralInvoiceFake:
        async def get_billing_period(
            self,
            received_payment_method: PaymentMethod,
            reference_month: str,
        ) -> tuple[date, date]:
            assert received_payment_method is payment_method
            assert reference_month == "2026-10"
            return date(2026, 9, 26), date(2026, 10, 26)

    provider: InvoicePeriodProviderProtocol = StructuralInvoiceFake()

    period = asyncio.run(provider.get_billing_period(payment_method, "2026-10"))
    assert period == (date(2026, 9, 26), date(2026, 10, 26))
