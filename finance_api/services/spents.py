import builtins
import uuid
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.core.logger import get_logger
from finance_api.models.categories import Category
from finance_api.models.payment_methods import PaymentMethod
from finance_api.models.spents import Spent
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.invoices import InvoiceRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.repositories.spents import SpentRepository
from finance_api.schemas.installments import InstallmentSummary
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.schemas.spents import SpentCreate, SpentUpdate
from finance_api.services.dashboard_strategies import (
    CivilMonthDashboardStrategy,
    DashboardPeriodStrategy,
    InvoicesDashboardStrategy,
)
from finance_api.services.invoices import InvoiceService
from finance_api.services.payment_resolution import PaymentResolutionService
from finance_api.services.update_preparation import (
    ExpenseCategoryStep,
    SpentPaymentStep,
    UpdateDataPreparer,
)

logger = get_logger(__name__)


class SpentService:
    def __init__(
        self,
        repo: SpentRepository,
        category_repo: CategoryRepository | None = None,
        pm_repo: PaymentMethodRepository | None = None,
        inv_service: InvoiceService | None = None,
        payment_resolver: PaymentResolutionService | None = None,
    ):
        self.repo = repo
        self._category_repo = category_repo
        self._pm_repo = pm_repo
        self._inv_service = inv_service
        self._payment_resolver = payment_resolver

    @property
    def category_repo(self) -> CategoryRepository:
        """Returns the injected category repo or instantiates one from CategoryRepository(self.repo.db)."""
        if self._category_repo is not None:
            return self._category_repo
        return CategoryRepository(self.repo.db)

    @property
    def pm_repo(self) -> PaymentMethodRepository:
        """Returns the injected payment method repo or instantiates one from PaymentMethodRepository(self.repo.db)."""
        if self._pm_repo is not None:
            return self._pm_repo
        return PaymentMethodRepository(self.repo.db)

    @property
    def inv_service(self) -> InvoiceService | None:
        """Returns the injected invoice service or instantiates one."""
        if self._inv_service is not None:
            return self._inv_service
        if hasattr(self.repo, "db") and self.repo.db is not None:
            return InvoiceService(InvoiceRepository(self.repo.db), self.pm_repo)
        return None

    @property
    def payment_resolver(self) -> PaymentResolutionService:
        """Returns the injected payment resolver or instantiates one."""
        if self._payment_resolver is not None:
            return self._payment_resolver
        return PaymentResolutionService(db=getattr(self.repo, "db", None))

    async def _validate_category(self, category_key: str) -> Category:
        category = await self.category_repo.get_by_key(category_key)
        if not category:
            raise ValidationError(
                f"Categoria '{category_key}' não existe. Por favor, crie-a primeiro."
            )
        return category

    async def _validate_payment_method(self, payment_method_key: str) -> PaymentMethod:
        payment_method = await self.pm_repo.get_by_key(payment_method_key)
        if not payment_method:
            raise ValidationError(
                f"Método de pagamento '{payment_method_key}' não existe. Por favor, crie-o primeiro."
            )
        return payment_method

    def _build_installments(self, spent: SpentCreate) -> list[Spent]:
        spents_to_create = []
        installment_id = uuid.uuid4()
        current = spent.current_installment or 1
        total = spent.total_installments or 2

        base_date = spent.created_at
        if base_date is None:
            base_date = datetime.now(ZoneInfo("America/Sao_Paulo"))

        months_to_add = 0
        for i in range(current, total + 1):
            spent_data = spent.model_dump(exclude={"is_installment"})
            spent_data["installment_id"] = installment_id
            spent_data["current_installment"] = i
            spent_data["total_installments"] = total

            new_spent = Spent(**spent_data)
            new_spent.created_at = base_date + relativedelta(months=months_to_add)
            spents_to_create.append(new_spent)
            months_to_add += 1

        return spents_to_create

    async def _resolve_invoice_periods(
        self,
        reference_month: str,
        inv_service: InvoiceService | None = None,
        pm_repo: PaymentMethodRepository | None = None,
    ) -> list[tuple[str, date, date]]:
        """Resolves invoice billing periods for all payment methods."""
        active_inv = inv_service or self.inv_service
        active_pm = pm_repo or self.pm_repo
        if not active_inv:
            raise ValidationError("InvoiceService não configurado para resolver faturas.")

        strategy = InvoicesDashboardStrategy(self.repo, active_inv, active_pm)
        return await strategy._resolve_invoice_periods(reference_month)

    @handle_service_errors
    async def create(self, spent: SpentCreate) -> "Spent":
        logger.info(f"Creating spent: {spent.amount} - {spent.category}")

        matched_category = await self._validate_category(spent.category)
        spent.category = matched_category.key

        if spent.payment_method is None:
            raise ValidationError("Método de pagamento é obrigatório.")

        matched_pm = await self._validate_payment_method(spent.payment_method)
        spent.payment_method = matched_pm.key

        resolved = await self.payment_resolver.resolve(
            matched_pm.key,
            requested_payment_type=spent.payment_type,
            is_credit_card_hint=matched_pm.is_credit_card,
        )
        if resolved.credit_card_id:
            spent.credit_card_id = resolved.credit_card_id
        if resolved.account_id:
            spent.account_id = resolved.account_id
        spent.payment_type = resolved.payment_type

        if spent.is_installment:
            spents_to_create = self._build_installments(spent)
            created_spents = await self.repo.create_many(spents_to_create)
            return created_spents[0]

        return await self.repo.create(spent)

    @handle_service_errors
    async def list(
        self,
        page: int = 1,
        size: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> PaginatedResponse["Spent"]:
        logger.info(f"Listing spents page {page} size {size} start {start_date} end {end_date}")
        skip = (page - 1) * size
        items, total = await self.repo.list(skip, size, start_date, end_date)
        return PaginatedResponse.create(items, total, page, size)

    @handle_service_errors
    async def get_dashboard(
        self,
        reference_month: str,
        mode: str,
        page: int,
        size: int,
        inv_service: InvoiceService | None = None,
        pm_repo: PaymentMethodRepository | None = None,
    ) -> PaginatedResponse["Spent"]:
        logger.info(f"Dashboard mode {mode} for {reference_month}")
        skip = (page - 1) * size

        active_inv = inv_service or self.inv_service
        active_pm = pm_repo or self.pm_repo

        if mode == "INVOICES" and not active_inv:
            raise ValidationError("InvoiceService não configurado para resolver faturas.")

        strategies: dict[str, DashboardPeriodStrategy] = {
            "CIVIL_MONTH": CivilMonthDashboardStrategy(self.repo),
        }
        if active_inv is not None:
            strategies["INVOICES"] = InvoicesDashboardStrategy(self.repo, active_inv, active_pm)

        strategy = strategies.get(mode)
        if strategy is None:
            raise ValidationError(f"Modo inválido: {mode}")

        items, total = await strategy.fetch_spents(reference_month, skip, size)
        return PaginatedResponse.create(list(items), total, page, size)

    @handle_service_errors
    async def get_by_id(self, spent_id: UUID) -> "Spent":
        logger.info(f"Getting spent by id: {spent_id}")
        spent = await self.repo.get_by_id(spent_id)
        if not spent:
            raise EntityNotFoundError(f"Gasto com ID {spent_id} não encontrado")
        return spent

    @handle_service_errors
    async def update(self, spent_id: UUID, update_data: SpentUpdate) -> "Spent":
        logger.info(f"Updating spent: {spent_id}")

        await self._build_update_preparer().prepare(update_data)

        current_spent = await self.repo.get_by_id(spent_id)
        if not current_spent:
            raise EntityNotFoundError(f"Gasto com ID {spent_id} não encontrado")

        updated_spent = await self.repo.update(spent_id, update_data)
        if not updated_spent:
            raise EntityNotFoundError(f"Gasto com ID {spent_id} não encontrado")
        return updated_spent

    def _build_update_preparer(self) -> UpdateDataPreparer[SpentUpdate]:
        """Builds the category/payment preparation chain used before persisting an update."""
        return UpdateDataPreparer(
            (
                ExpenseCategoryStep(self.category_repo),
                SpentPaymentStep(self.pm_repo, self.payment_resolver),
            )
        )

    @handle_service_errors
    async def delete(self, spent_id: UUID) -> bool:
        logger.info(f"Deleting spent: {spent_id}")
        deleted = await self.repo.delete(spent_id)
        if not deleted:
            raise EntityNotFoundError(f"Gasto com ID {spent_id} não encontrado")
        return True

    @handle_service_errors
    async def get_installments_summary(self) -> builtins.list[InstallmentSummary]:
        logger.info("Fetching installments summary")
        summary_dicts = await self.repo.get_installments_summary()
        return [InstallmentSummary(**s) for s in summary_dicts]
