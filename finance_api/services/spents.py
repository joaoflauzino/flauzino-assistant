from datetime import date, datetime
import uuid
from typing import Optional, List
from uuid import UUID
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo
import calendar

from finance_api.models.spents import Spent
from finance_api.repositories.spents import SpentRepository
from finance_api.repositories.categories import CategoryRepository
from finance_api.schemas.spents import SpentCreate, SpentUpdate
from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.schemas.installments import InstallmentSummary
from finance_api.core.logger import get_logger

logger = get_logger(__name__)


class SpentService:
    def __init__(self, repo: SpentRepository):
        self.repo = repo

    @handle_service_errors
    async def create(self, spent: SpentCreate) -> "Spent":
        logger.info(f"Creating spent: {spent.amount} - {spent.category}")

        # Validate category exists in database
        category_repo = CategoryRepository(self.repo.db)
        if not await category_repo.get_by_key(spent.category):
            raise ValidationError(
                f"Category '{spent.category}' does not exist. Please create it first."
            )

        if spent.is_installment:
            installment_id = uuid.uuid4()
            current = spent.current_installment or 1
            total = spent.total_installments or current

            spents_to_create = []
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
        self, reference_month: str, mode: str, page: int, size: int, inv_service, pm_repo
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
            payment_methods, _ = await pm_repo.list(page=1, size=1000)
            periods = []
            for pm in payment_methods:
                start_d, end_d = await inv_service.get_invoice_dates(pm, reference_month)
                periods.append((pm.key, start_d, end_d))

            items, total = await self.repo.list_by_multiple_periods(periods, skip, size)
            return PaginatedResponse.create(items, total, page, size)
        else:
            raise ValidationError(f"Invalid mode: {mode}")

    @handle_service_errors
    async def get_by_id(self, spent_id: UUID) -> "Spent":
        logger.info(f"Getting spent by id: {spent_id}")
        spent = await self.repo.get_by_id(spent_id)
        if not spent:
            raise EntityNotFoundError(f"Spent with id {spent_id} not found")
        return spent

    @handle_service_errors
    async def update(self, spent_id: UUID, update_data: SpentUpdate) -> "Spent":
        logger.info(f"Updating spent: {spent_id}")

        # Validate category exists if being updated
        if update_data.category:
            category_repo = CategoryRepository(self.repo.db)
            if not await category_repo.get_by_key(update_data.category):
                raise ValidationError(
                    f"Category '{update_data.category}' does not exist. Please create it first."
                )

        current_spent = await self.repo.get_by_id(spent_id)
        if not current_spent:
            raise EntityNotFoundError(f"Spent with id {spent_id} not found")

        updated_spent = await self.repo.update(spent_id, update_data)
        if not updated_spent:
            raise EntityNotFoundError(f"Spent with id {spent_id} not found")
        return updated_spent

    @handle_service_errors
    async def delete(self, spent_id: UUID) -> bool:
        logger.info(f"Deleting spent: {spent_id}")
        deleted = await self.repo.delete(spent_id)
        if not deleted:
            raise EntityNotFoundError(f"Spent with id {spent_id} not found")
        return True

    @handle_service_errors
    async def get_installments_summary(self) -> List[InstallmentSummary]:
        logger.info("Fetching installments summary")
        summary_dicts = await self.repo.get_installments_summary()
        return [InstallmentSummary(**s) for s in summary_dicts]
