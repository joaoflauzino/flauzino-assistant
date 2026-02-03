from datetime import date
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from finance_api.models.limits import SpendingLimit

from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.schemas.limits import SpendingLimitCreate, SpendingLimitUpdate
from finance_api.core.decorators import handle_limits_errors
from finance_api.core.exceptions import EntityNotFoundError
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.core.logger import get_logger

logger = get_logger(__name__)


class SpendingLimitService:
    def __init__(self, repo: SpendingLimitRepository):
        self.repo = repo

    @handle_limits_errors
    async def create(self, limit_data: SpendingLimitCreate) -> "SpendingLimit":
        logger.info(f"Creating spending limit for category: {limit_data.category}")
        return await self.repo.create(limit_data)

    @handle_limits_errors
    async def list(
        self,
        page: int = 1,
        size: int = 10,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> PaginatedResponse["SpendingLimit"]:
        logger.info(f"Listing spending limits page {page} size {size} start {start_date} end {end_date}")
        skip = (page - 1) * size
        items, total = await self.repo.list(skip, size, start_date, end_date)
        return PaginatedResponse.create(items, total, page, size)

    @handle_limits_errors
    async def get_by_category(self, category: str) -> Optional["SpendingLimit"]:
        logger.info(f"Getting spending limit by category: {category}")
        return await self.repo.get_by_category(category)

    @handle_limits_errors
    async def get_by_id(self, limit_id: UUID) -> "SpendingLimit":
        logger.info(f"Getting spending limit by id: {limit_id}")
        limit = await self.repo.get_by_id(limit_id)
        if not limit:
            raise EntityNotFoundError(f"Spending limit with id {limit_id} not found")
        return limit

    @handle_limits_errors
    async def update(
        self, limit_id: UUID, update_data: SpendingLimitUpdate
    ) -> "SpendingLimit":
        logger.info(f"Updating spending limit: {limit_id}")
        updated_limit = await self.repo.update(limit_id, update_data)
        if not updated_limit:
            raise EntityNotFoundError(f"Spending limit with id {limit_id} not found")
        return updated_limit

    @handle_limits_errors
    async def delete(self, limit_id: UUID) -> bool:
        logger.info(f"Deleting spending limit: {limit_id}")
        deleted = await self.repo.delete(limit_id)
        if not deleted:
            raise EntityNotFoundError(f"Spending limit with id {limit_id} not found")
        return True
