from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo
from typing import Optional, List
from uuid import UUID

from finance_api.models.limits import SpendingLimit

from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.spents import SpentRepository
from finance_api.schemas.limits import SpendingLimitCreate, SpendingLimitUpdate, CategoryBalance
from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.core.logger import get_logger

logger = get_logger(__name__)


class SpendingLimitService:
    def __init__(self, repo: SpendingLimitRepository):
        self.repo = repo

    @handle_service_errors
    async def create(self, limit_data: SpendingLimitCreate) -> "SpendingLimit":
        logger.info(f"Creating spending limit for category: {limit_data.category}")

        # Validate category exists in database
        category_repo = CategoryRepository(self.repo.db)
        if not await category_repo.get_by_key(limit_data.category):
            raise ValidationError(
                f"Categoria '{limit_data.category}' não existe. Por favor, crie-a primeiro."
            )

        return await self.repo.create(limit_data)

    @handle_service_errors
    async def list(
        self,
        page: int = 1,
        size: int = 10,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> PaginatedResponse["SpendingLimit"]:
        logger.info(
            f"Listing spending limits page {page} size {size} start {start_date} end {end_date}"
        )
        skip = (page - 1) * size
        items, total = await self.repo.list(skip, size, start_date, end_date)
        return PaginatedResponse.create(items, total, page, size)

    @handle_service_errors
    async def get_by_category(self, category: str) -> Optional["SpendingLimit"]:
        logger.info(f"Getting spending limit by category: {category}")
        return await self.repo.get_by_category(category)

    @handle_service_errors
    async def get_by_id(self, limit_id: UUID) -> "SpendingLimit":
        logger.info(f"Getting spending limit by id: {limit_id}")
        limit = await self.repo.get_by_id(limit_id)
        if not limit:
            raise EntityNotFoundError(f"Limite de gastos com ID {limit_id} não encontrado")
        return limit

    @handle_service_errors
    async def update(self, limit_id: UUID, update_data: SpendingLimitUpdate) -> "SpendingLimit":
        logger.info(f"Updating spending limit: {limit_id}")
        updated_limit = await self.repo.update(limit_id, update_data)
        if not updated_limit:
            raise EntityNotFoundError(f"Limite de gastos com ID {limit_id} não encontrado")
        return updated_limit

    @handle_service_errors
    async def delete(self, limit_id: UUID) -> bool:
        logger.info(f"Deleting spending limit: {limit_id}")
        deleted = await self.repo.delete(limit_id)
        if not deleted:
            raise EntityNotFoundError(f"Limite de gastos com ID {limit_id} não encontrado")
        return True

    @handle_service_errors
    async def get_balance(
        self, reference_month: Optional[str], pm_repo, inv_service
    ) -> List["CategoryBalance"]:
        # Get all categories that have limits
        limits, _ = await self.repo.list(skip=0, limit=1000)

        # Get all spents based on invoices
        payment_methods, _ = await pm_repo.list(page=1, size=1000)
        periods = []

        today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

        for pm in payment_methods:
            if not reference_month:
                current_month_str = today.strftime("%Y-%m")
                start_d, end_d = await inv_service.get_invoice_dates(pm, current_month_str)
                logger.info(
                    f"[{pm.key}] Checking today {today} against start {start_d} end {end_d} for month {current_month_str}"
                )
                if today > end_d:
                    next_month = today + relativedelta(months=1)
                    start_d, end_d = await inv_service.get_invoice_dates(
                        pm, next_month.strftime("%Y-%m")
                    )
                    logger.info(
                        f"[{pm.key}] After today > end_d, shifted to {next_month.strftime('%Y-%m')}: start {start_d} end {end_d}"
                    )
                elif today < start_d:
                    prev_month = today - relativedelta(months=1)
                    start_d, end_d = await inv_service.get_invoice_dates(
                        pm, prev_month.strftime("%Y-%m")
                    )
                    logger.info(
                        f"[{pm.key}] After today < start_d, shifted to {prev_month.strftime('%Y-%m')}: start {start_d} end {end_d}"
                    )
            else:
                start_d, end_d = await inv_service.get_invoice_dates(pm, reference_month)

            periods.append((pm.key, start_d, end_d))

        spent_repo = SpentRepository(self.repo.db)
        spents, _ = await spent_repo.list_by_multiple_periods(periods, skip=0, limit=10000)

        # Aggregate spents by category
        spent_by_category = {}
        for s in spents:
            spent_by_category[s.category] = spent_by_category.get(s.category, 0.0) + s.amount

        # Get category display names
        category_repo = CategoryRepository(self.repo.db)
        categories, _ = await category_repo.list(skip=0, limit=1000)
        cat_map = {c.key: c.display_name for c in categories}

        balances = []
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
