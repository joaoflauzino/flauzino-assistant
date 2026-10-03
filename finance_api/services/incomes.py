import calendar
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

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

logger = get_logger(__name__)


def _parse_reference_month(reference_month: Optional[str]) -> tuple[str, date, date]:
    if not reference_month:
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        reference_month = now.strftime("%Y-%m")

    try:
        parsed_date = datetime.strptime(reference_month, "%Y-%m")
    except ValueError as e:
        raise ValidationError("Formato de mês inválido. Use YYYY-MM.") from e

    year, month = parsed_date.year, parsed_date.month
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)

    return reference_month, start_date, end_date


class IncomeService:
    def __init__(
        self,
        repo: IncomeRepository,
        category_repo: Optional[IncomeCategoryRepository] = None,
        pm_repo: Optional[PaymentMethodRepository] = None,
        spent_repo: Optional[SpentRepository] = None,
    ):
        self.repo = repo
        self._category_repo = category_repo
        self._pm_repo = pm_repo
        self._spent_repo = spent_repo

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
            await self._validate_payment_method(income_data.payment_method)

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
            await self._validate_payment_method(update_data.payment_method)

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
        self, reference_month: Optional[str] = None
    ) -> MonthlyBalanceSummary:
        ref_month, start_date, end_date = _parse_reference_month(reference_month)
        logger.info(f"Calculating monthly balance summary for {ref_month}")

        incomes = await self.repo.list_by_period(start_date, end_date)
        spents, _ = await self.spent_repo.list(
            skip=0, limit=100000, start_date=start_date, end_date=end_date
        )

        total_incomes = round(sum(i.amount for i in incomes), 2)
        total_spents = round(sum(s.amount for s in spents), 2)
        net_balance = round(total_incomes - total_spents, 2)
        is_positive = net_balance >= 0
        savings_rate = round((net_balance / total_incomes) * 100, 2) if total_incomes > 0 else 0.0

        incomes_by_category: dict[str, float] = {}
        for inc in incomes:
            incomes_by_category[inc.category] = round(
                incomes_by_category.get(inc.category, 0.0) + inc.amount, 2
            )

        spents_by_category: dict[str, float] = {}
        for sp in spents:
            spents_by_category[sp.category] = round(
                spents_by_category.get(sp.category, 0.0) + sp.amount, 2
            )

        return MonthlyBalanceSummary(
            reference_month=ref_month,
            total_incomes=total_incomes,
            total_spents=total_spents,
            net_balance=net_balance,
            is_positive=is_positive,
            savings_rate=savings_rate,
            incomes_by_category=incomes_by_category,
            spents_by_category=spents_by_category,
        )
