from collections.abc import Sequence
from datetime import date
from typing import Protocol

from finance_api.core.dates import DateRange
from finance_api.models.spents import Spent
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.repositories.spents import SpentRepository
from finance_api.services.invoices import InvoiceService


class DashboardPeriodStrategy(Protocol):
    """Protocol contract for resolving dashboard spents based on a chosen period strategy."""

    async def fetch_spents(
        self,
        reference_month: str,
        skip: int,
        size: int,
    ) -> tuple[Sequence[Spent], int]: ...


class CivilMonthDashboardStrategy:
    """Fetches spents filtered strictly by the civil calendar month (1st to last day)."""

    def __init__(self, spent_repo: SpentRepository) -> None:
        self._repo = spent_repo

    async def fetch_spents(
        self,
        reference_month: str,
        skip: int,
        size: int,
    ) -> tuple[Sequence[Spent], int]:
        period = DateRange.from_reference_month(reference_month)
        return await self._repo.list(skip, size, period.start, period.end)


class InvoicesDashboardStrategy:
    """Fetches spents grouped by credit card invoice billing periods and civil month for accounts."""

    def __init__(
        self,
        spent_repo: SpentRepository,
        inv_service: InvoiceService,
        pm_repo: PaymentMethodRepository,
    ) -> None:
        self._repo = spent_repo
        self._inv_service = inv_service
        self._pm_repo = pm_repo

    async def _resolve_invoice_periods(self, reference_month: str) -> list[tuple[str, date, date]]:
        payment_methods, _ = await self._pm_repo.list(page=1, size=1000)
        periods: list[tuple[str, date, date]] = []

        civil_period = DateRange.from_reference_month(reference_month)

        for pm in payment_methods:
            if pm.is_credit_card:
                start_d, end_d = await self._inv_service.get_billing_period(pm, reference_month)
            else:
                start_d, end_d = civil_period.start, civil_period.end
            periods.append((pm.key, start_d, end_d))

        return periods

    async def fetch_spents(
        self,
        reference_month: str,
        skip: int,
        size: int,
    ) -> tuple[Sequence[Spent], int]:
        periods = await self._resolve_invoice_periods(reference_month)
        return await self._repo.list_by_multiple_periods(periods, skip, size)
