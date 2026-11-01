from datetime import date
from typing import List, Optional
from uuid import UUID

from finance_api.core.dates import DateRange
from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.core.logger import get_logger
from finance_api.models.income_categories import IncomeCategory
from finance_api.models.payment_methods import PaymentMethod
from finance_api.repositories.income_categories import IncomeCategoryRepository
from finance_api.repositories.incomes import IncomeRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.repositories.spents import SpentRepository
from finance_api.schemas.incomes import (
    IncomeCreate,
    IncomeResponse,
    IncomeUpdate,
    MonthlyBalanceSummary,
)
from finance_api.services.payment_resolution import PaymentResolutionService

logger = get_logger(__name__)


class IncomeService:
    def __init__(
        self,
        repo: IncomeRepository,
        category_repo: Optional[IncomeCategoryRepository] = None,
        pm_repo: Optional[PaymentMethodRepository] = None,
        spent_repo: Optional[SpentRepository] = None,
        payment_resolver: Optional[PaymentResolutionService] = None,
    ):
        self.repo = repo
        self._category_repo = category_repo
        self._pm_repo = pm_repo
        self._spent_repo = spent_repo
        self._payment_resolver = payment_resolver

    @property
    def category_repo(self) -> IncomeCategoryRepository:
        if self._category_repo is not None:
            return self._category_repo
        return IncomeCategoryRepository(self.repo.db)

    @property
    def pm_repo(self) -> PaymentMethodRepository:
        if self._pm_repo is not None:
            return self._pm_repo
        return PaymentMethodRepository(self.repo.db)

    @property
    def spent_repo(self) -> SpentRepository:
        if self._spent_repo is not None:
            return self._spent_repo
        return SpentRepository(self.repo.db)

    @property
    def payment_resolver(self) -> PaymentResolutionService:
        if self._payment_resolver is not None:
            return self._payment_resolver
        return PaymentResolutionService(db=getattr(self.repo, "db", None))

    async def _validate_category(self, category_key: str) -> IncomeCategory:
        category = await self.category_repo.get_by_key(category_key)
        if not category:
            raise ValidationError(
                f"Categoria de receita '{category_key}' não existe. Por favor, crie-a primeiro."
            )
        return category

    async def _validate_payment_method(self, pm_key: str) -> PaymentMethod:
        pm = await self.pm_repo.get_by_key(pm_key)
        if not pm:
            raise ValidationError(f"Método de pagamento '{pm_key}' não existe.")
        return pm

    @handle_service_errors
    async def create(self, income_data: IncomeCreate) -> IncomeResponse:
        await self._validate_category(income_data.category)
        if income_data.payment_method:
            matched_pm = await self._validate_payment_method(income_data.payment_method)
            income_data.payment_method = matched_pm.key
            if not income_data.account_id:
                resolved = await self.payment_resolver.resolve(matched_pm.key)
                if resolved.account_id:
                    income_data.account_id = resolved.account_id

        logger.info(f"Creating income: {income_data.description} ({income_data.amount})")
        income = await self.repo.create(income_data)
        return IncomeResponse.model_validate(income)

    @handle_service_errors
    async def list(
        self,
        page: int = 1,
        size: int = 100,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
    ) -> tuple[List[IncomeResponse], int]:
        skip = (page - 1) * size
        logger.info(f"Listing incomes page={page} size={size}")
        items, total = await self.repo.list(
            skip=skip,
            limit=size,
            start_date=start_date,
            end_date=end_date,
            category=category,
        )
        return [IncomeResponse.model_validate(item) for item in items], total

    @handle_service_errors
    async def get_by_id(self, income_id: UUID) -> IncomeResponse:
        logger.info(f"Getting income: {income_id}")
        income = await self.repo.get_by_id(income_id)
        if not income:
            raise EntityNotFoundError(f"Receita {income_id} não encontrada")
        return IncomeResponse.model_validate(income)

    @handle_service_errors
    async def update(self, income_id: UUID, update_data: IncomeUpdate) -> IncomeResponse:
        if update_data.category:
            await self._validate_category(update_data.category)
        if update_data.payment_method:
            matched_pm = await self._validate_payment_method(update_data.payment_method)
            update_data.payment_method = matched_pm.key
            if not getattr(update_data, "account_id", None):
                resolved = await self.payment_resolver.resolve(matched_pm.key)
                if resolved.account_id:
                    update_data.account_id = resolved.account_id

        logger.info(f"Updating income: {income_id}")
        income = await self.repo.update(income_id, update_data)
        if not income:
            raise EntityNotFoundError(f"Receita {income_id} não encontrada")
        return IncomeResponse.model_validate(income)

    @handle_service_errors
    async def delete(self, income_id: UUID) -> bool:
        logger.info(f"Deleting income: {income_id}")
        success = await self.repo.delete(income_id)
        if not success:
            raise EntityNotFoundError(f"Receita {income_id} não encontrada")
        return success

    @handle_service_errors
    async def get_monthly_summary(
        self,
        reference_month: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> MonthlyBalanceSummary:
        period = DateRange.from_bounds(start_date, end_date, reference_month)
        logger.info(f"Calculating balance summary for {period.label} ({period.start} to {period.end})")

        incomes = await self.repo.list_by_period(period.start, period.end)
        spents, _ = await self.spent_repo.list(
            skip=0, limit=10000, start_date=period.start, end_date=period.end
        )

        total_incomes = sum(inc.amount for inc in incomes)
        total_spents = sum(sp.amount for sp in spents)
        net_balance = round(total_incomes - total_spents, 2)
        is_positive = net_balance >= 0

        savings_rate = 0.0
        if total_incomes > 0:
            savings_rate = round((net_balance / total_incomes) * 100, 2)

        incomes_by_category: dict[str, float] = {}
        for inc in incomes:
            cat = inc.category
            incomes_by_category[cat] = round(incomes_by_category.get(cat, 0.0) + inc.amount, 2)

        spents_by_category: dict[str, float] = {}
        for sp in spents:
            cat = sp.category
            spents_by_category[cat] = round(spents_by_category.get(cat, 0.0) + sp.amount, 2)

        return MonthlyBalanceSummary(
            reference_month=period.label,
            total_incomes=round(total_incomes, 2),
            total_spents=round(total_spents, 2),
            net_balance=net_balance,
            is_positive=is_positive,
            savings_rate=savings_rate,
            incomes_by_category=incomes_by_category,
            spents_by_category=spents_by_category,
        )
