from datetime import date
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from finance_api.models.spents import Spent

from finance_api.repositories.spents import SpentRepository
from finance_api.repositories.categories import CategoryRepository
from finance_api.schemas.spents import SpentCreate, SpentUpdate
from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.schemas.pagination import PaginatedResponse
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

        return await self.repo.create(spent)

    @handle_service_errors
    async def list(
        self,
        page: int = 1,
        size: int = 10,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> PaginatedResponse["Spent"]:
        logger.info(
            f"Listing spents page {page} size {size} start {start_date} end {end_date}"
        )
        skip = (page - 1) * size
        items, total = await self.repo.list(skip, size, start_date, end_date)
        return PaginatedResponse.create(items, total, page, size)

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
