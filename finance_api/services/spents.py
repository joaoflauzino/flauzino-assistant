import calendar
from datetime import date, datetime
from typing import List, Optional, Tuple
import uuid
from uuid import UUID
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta
from sqlalchemy import select

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
from finance_api.services.invoices import InvoiceService

logger = get_logger(__name__)


class SpentService:
    def __init__(
        self,
        repo: SpentRepository,
        category_repo: Optional[CategoryRepository] = None,
        pm_repo: Optional[PaymentMethodRepository] = None,
        inv_service: Optional[InvoiceService] = None,
    ):
        self.repo = repo
        self._category_repo = category_repo
        self._pm_repo = pm_repo
        self._inv_service = inv_service

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
    def inv_service(self) -> Optional[InvoiceService]:
        """Returns the injected invoice service or instantiates one."""
        if self._inv_service is not None:
            return self._inv_service
        if hasattr(self.repo, "db") and self.repo.db is not None:
            return InvoiceService(InvoiceRepository(self.repo.db), self.pm_repo)
        return None

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

    def _build_installments(self, spent: SpentCreate) -> List[Spent]:
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
        inv_service: Optional[InvoiceService] = None,
        pm_repo: Optional[PaymentMethodRepository] = None,
    ) -> List[Tuple[str, date, date]]:
        """Resolves invoice billing periods for all payment methods.

        For credit cards, uses the calculated or configured invoice dates.
        For non-credit cards (Pix, Dinheiro, Débito, etc.), uses the civil month period.
        """
        active_inv = inv_service or self.inv_service
        active_pm = pm_repo or self.pm_repo
        if not active_inv:
            raise ValidationError("InvoiceService não configurado para resolver faturas.")

        payment_methods, _ = await active_pm.list(page=1, size=1000)
        periods: List[Tuple[str, date, date]] = []

        year, month = map(int, reference_month.split("-"))
        _, last_day = calendar.monthrange(year, month)
        civil_start = date(year, month, 1)
        civil_end = date(year, month, last_day)

        for pm in payment_methods:
            if pm.is_credit_card:
                start_d, end_d = await active_inv.get_invoice_dates(pm, reference_month)
            else:
                start_d, end_d = civil_start, civil_end
            periods.append((pm.key, start_d, end_d))
        return periods

    @handle_service_errors
    async def create(self, spent: SpentCreate) -> "Spent":
        logger.info(f"Creating spent: {spent.amount} - {spent.category}")

        matched_category = await self._validate_category(spent.category)
        spent.category = matched_category.key

        matched_pm = await self._validate_payment_method(spent.payment_method)
        spent.payment_method = matched_pm.key

        user_payment_type = (
            spent.payment_type
            if spent.payment_type in ("PIX", "DEBIT", "CASH", "TRANSFER", "OTHER")
            else None
        )

        card = None
        try:
            from finance_api.models.credit_cards import CreditCard

            card_res = await self.repo.db.execute(
                select(CreditCard).where(CreditCard.key == matched_pm.key)
            )
            card = card_res.scalar_one_or_none()
            if card:
                spent.credit_card_id = card.id
                spent.account_id = card.account_id
                spent.payment_type = "CREDIT"
        except Exception:
            pass

        if not card:
            try:
                from finance_api.models.accounts import Account

                acc_res = await self.repo.db.execute(
                    select(Account).where(Account.key == matched_pm.key)
                )
                acc = acc_res.scalar_one_or_none()
                if acc:
                    spent.account_id = acc.id
                    spent.payment_type = user_payment_type or "DEBIT"
            except Exception:
                pass

        if not getattr(spent, "account_id", None) and not card:
            spent.payment_type = user_payment_type or (
                "CREDIT" if getattr(matched_pm, "is_credit_card", False) else "DEBIT"
            )

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
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
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
        inv_service: Optional[InvoiceService] = None,
        pm_repo: Optional[PaymentMethodRepository] = None,
    ) -> PaginatedResponse["Spent"]:
        logger.info(f"Dashboard mode {mode} for {reference_month}")
        skip = (page - 1) * size

        if mode == "CIVIL_MONTH":
            year, month = map(int, reference_month.split("-"))
            _, last_day = calendar.monthrange(year, month)
            start_date = date(year, month, 1)
            end_date = date(year, month, last_day)
            items, total = await self.repo.list(skip, size, start_date, end_date)
            return PaginatedResponse.create(items, total, page, size)

        elif mode == "INVOICES":
            periods = await self._resolve_invoice_periods(
                reference_month=reference_month,
                inv_service=inv_service,
                pm_repo=pm_repo,
            )
            items, total = await self.repo.list_by_multiple_periods(periods, skip, size)
            return PaginatedResponse.create(items, total, page, size)
        else:
            raise ValidationError(f"Modo inválido: {mode}")

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

        if update_data.category:
            matched_cat = await self._validate_category(update_data.category)
            update_data.category = matched_cat.key

        if update_data.payment_method:
            matched_pm = await self._validate_payment_method(update_data.payment_method)
            update_data.payment_method = matched_pm.key
            user_payment_type = update_data.payment_type

            card = None
            try:
                from finance_api.models.credit_cards import CreditCard

                card_res = await self.repo.db.execute(
                    select(CreditCard).where(CreditCard.key == matched_pm.key)
                )
                card = card_res.scalar_one_or_none()
                if card:
                    update_data.credit_card_id = card.id
                    update_data.account_id = card.account_id
                    update_data.payment_type = "CREDIT"
            except Exception:
                pass

            if not card:
                try:
                    from finance_api.models.accounts import Account

                    acc_res = await self.repo.db.execute(
                        select(Account).where(Account.key == matched_pm.key)
                    )
                    acc = acc_res.scalar_one_or_none()
                    if acc:
                        update_data.account_id = acc.id
                        update_data.payment_type = user_payment_type or "DEBIT"
                except Exception:
                    pass

            if not getattr(update_data, "account_id", None) and not card:
                update_data.payment_type = user_payment_type or (
                    "CREDIT" if getattr(matched_pm, "is_credit_card", False) else "DEBIT"
                )

        current_spent = await self.repo.get_by_id(spent_id)
        if not current_spent:
            raise EntityNotFoundError(f"Gasto com ID {spent_id} não encontrado")

        updated_spent = await self.repo.update(spent_id, update_data)
        if not updated_spent:
            raise EntityNotFoundError(f"Gasto com ID {spent_id} não encontrado")
        return updated_spent

    @handle_service_errors
    async def delete(self, spent_id: UUID) -> bool:
        logger.info(f"Deleting spent: {spent_id}")
        deleted = await self.repo.delete(spent_id)
        if not deleted:
            raise EntityNotFoundError(f"Gasto com ID {spent_id} não encontrado")
        return True

    @handle_service_errors
    async def get_installments_summary(self) -> List[InstallmentSummary]:
        logger.info("Fetching installments summary")
        summary_dicts = await self.repo.get_installments_summary()
        return [InstallmentSummary(**s) for s in summary_dicts]
