from datetime import date
from uuid import UUID

from finance_api.core.dates import DateRange
from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.core.logger import get_logger
from finance_api.models.income_categories import IncomeCategory
from finance_api.models.payment_methods import PaymentMethod
from finance_api.repositories.protocols import (
    IncomeCategoryRepositoryProtocol,
    IncomeRepositoryProtocol,
    PaymentMethodRepositoryProtocol,
    SpentRepositoryProtocol,
)
from finance_api.schemas.incomes import (
    IncomeCreate,
    IncomeResponse,
    IncomeUpdate,
    MonthlyBalanceSummary,
)
from finance_api.services.payment_resolution_protocols import PaymentResolutionServiceProtocol
from finance_api.services.update_preparation import (
    IncomeCategoryStep,
    IncomePaymentStep,
    UpdateDataPreparer,
)
from finance_api.services.utils import build_monthly_summary

logger = get_logger(__name__)

MONTHLY_SUMMARY_SPENT_LIMIT = 10_000


class IncomeService:
    def __init__(
        self,
        repo: IncomeRepositoryProtocol,
        category_repo: IncomeCategoryRepositoryProtocol,
        pm_repo: PaymentMethodRepositoryProtocol,
        spent_repo: SpentRepositoryProtocol,
        payment_resolver: PaymentResolutionServiceProtocol,
    ) -> None:
        self.repo = repo
        self.category_repo = category_repo
        self.pm_repo = pm_repo
        self.spent_repo = spent_repo
        self.payment_resolver = payment_resolver

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
        """Creates an income, normalizing the supplied payload in place."""
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
        start_date: date | None = None,
        end_date: date | None = None,
        category: str | None = None,
    ) -> tuple[list[IncomeResponse], int]:
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
        """Updates an income after preparing the payload in place."""
        await self._build_update_preparer().prepare(update_data)

        logger.info(f"Updating income: {income_id}")
        income = await self.repo.update(income_id, update_data)
        if not income:
            raise EntityNotFoundError(f"Receita {income_id} não encontrada")
        return IncomeResponse.model_validate(income)

    def _build_update_preparer(self) -> UpdateDataPreparer[IncomeUpdate]:
        """Builds the category/payment preparation chain used before persisting an update."""
        return UpdateDataPreparer(
            (
                IncomeCategoryStep(self.category_repo),
                IncomePaymentStep(self.pm_repo, self.payment_resolver),
            )
        )

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
        reference_month: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> MonthlyBalanceSummary:
        period = DateRange.from_bounds(start_date, end_date, reference_month)
        logger.info(
            f"Calculating balance summary for {period.label} ({period.start} to {period.end})"
        )

        incomes = await self.repo.list_by_period(period.start, period.end)
        spents, _ = await self.spent_repo.list(
            skip=0,
            limit=MONTHLY_SUMMARY_SPENT_LIMIT,
            start_date=period.start,
            end_date=period.end,
        )

        return build_monthly_summary(period.label, incomes, spents)
