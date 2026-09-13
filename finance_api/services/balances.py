from datetime import date, datetime
from typing import List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta

from finance_api.core.decorators import handle_service_errors
from finance_api.core.logger import get_logger
from finance_api.models.limits import SpendingLimit
from finance_api.models.payment_methods import PaymentMethod
from finance_api.models.spents import Spent
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.repositories.spents import SpentRepository
from finance_api.schemas.limits import CategoryBalance
from finance_api.services.invoices import InvoiceService

logger = get_logger(__name__)


class BalanceService:
    def __init__(
        self,
        limit_repo: SpendingLimitRepository,
        spent_repo: SpentRepository,
        category_repo: CategoryRepository,
        pm_repo: PaymentMethodRepository,
        inv_service: InvoiceService,
    ):
        self.limit_repo = limit_repo
        self.spent_repo = spent_repo
        self.category_repo = category_repo
        self.pm_repo = pm_repo
        self.inv_service = inv_service

    @handle_service_errors
    async def get_balance(self, reference_month: Optional[str] = None) -> List[CategoryBalance]:
        """Orchestrates fetching data and calculating category balances for a reference month."""
        logger.info(f"Getting balances for reference_month={reference_month}")
        today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

        # 1. Fetch spending limits and payment methods
        limits, _ = await self.limit_repo.list(skip=0, limit=1000)
        payment_methods, _ = await self.pm_repo.list(page=1, size=1000)

        # 2. Resolve invoice periods for each payment method
        periods = await self._resolve_periods(payment_methods, reference_month, today)

        # 3. Fetch spents for all resolved periods and aggregate by category
        spents, _ = await self.spent_repo.list_by_multiple_periods(periods, skip=0, limit=10000)
        spent_by_category = self._aggregate_spents_by_category(spents)

        # 4. Fetch category display names
        categories, _ = await self.category_repo.list(skip=0, limit=1000)
        cat_map = {c.key: c.display_name for c in categories}

        # 5. Build balances
        return self._build_balances(limits, spent_by_category, cat_map)

    async def _resolve_periods(
        self,
        payment_methods: Sequence[PaymentMethod],
        reference_month: Optional[str],
        today: date,
    ) -> List[Tuple[str, date, date]]:
        """Resolves billing period (start_date, end_date) for each payment method."""
        periods: List[Tuple[str, date, date]] = []
        for pm in payment_methods:
            start_d, end_d = await self._resolve_pm_invoice_period(
                pm=pm, reference_month=reference_month, today=today
            )
            periods.append((pm.key, start_d, end_d))
        return periods

    async def _resolve_pm_invoice_period(
        self,
        pm: PaymentMethod,
        reference_month: Optional[str],
        today: date,
    ) -> Tuple[date, date]:
        """Resolves invoice start and end dates for a payment method based on current date or reference month."""
        if reference_month:
            return await self.inv_service.get_invoice_dates(pm, reference_month)

        current_month_str = today.strftime("%Y-%m")
        start_d, end_d = await self.inv_service.get_invoice_dates(pm, current_month_str)
        logger.info(
            f"[{pm.key}] Checking today {today} against start {start_d} end {end_d} for month {current_month_str}"
        )

        if today > end_d:
            next_month = today + relativedelta(months=1)
            start_d, end_d = await self.inv_service.get_invoice_dates(
                pm, next_month.strftime("%Y-%m")
            )
            logger.info(
                f"[{pm.key}] After today > end_d, shifted to {next_month.strftime('%Y-%m')}: start {start_d} end {end_d}"
            )
        elif today < start_d:
            prev_month = today - relativedelta(months=1)
            start_d, end_d = await self.inv_service.get_invoice_dates(
                pm, prev_month.strftime("%Y-%m")
            )
            logger.info(
                f"[{pm.key}] After today < start_d, shifted to {prev_month.strftime('%Y-%m')}: start {start_d} end {end_d}"
            )

        return start_d, end_d

    def _aggregate_spents_by_category(self, spents: Sequence[Spent]) -> dict[str, float]:
        """Aggregates spent amounts by category key."""
        spent_by_category: dict[str, float] = {}
        for s in spents:
            spent_by_category[s.category] = spent_by_category.get(s.category, 0.0) + s.amount
        return spent_by_category

    def _build_balances(
        self,
        limits: Sequence[SpendingLimit],
        spent_by_category: dict[str, float],
        cat_map: dict[str, str],
    ) -> List[CategoryBalance]:
        """Calculates available balance and percentage used for each category."""
        balances: List[CategoryBalance] = []
        processed_cats = set()

        for limit in limits:
            cat_key = limit.category
            cat_display = cat_map.get(cat_key, cat_key)
            spent = spent_by_category.get(cat_key, 0.0)
            available = limit.amount - spent
            percentage = (spent / limit.amount) * 100 if limit.amount > 0 else 100.0

            balances.append(
                CategoryBalance(
                    category=cat_key,
                    category_display_name=cat_display,
                    limit=limit.amount,
                    spent=spent,
                    available=available,
                    percentage_used=percentage,
                )
            )
            processed_cats.add(cat_key)

        for cat_key, spent in spent_by_category.items():
            if cat_key not in processed_cats and spent > 0:
                cat_display = cat_map.get(cat_key, cat_key)
                balances.append(
                    CategoryBalance(
                        category=cat_key,
                        category_display_name=cat_display,
                        limit=0.0,
                        spent=spent,
                        available=-spent,
                        percentage_used=100.0,
                    )
                )

        return balances
