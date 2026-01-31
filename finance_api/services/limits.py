from uuid import UUID

from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.schemas.limits import SpendingLimitCreate, SpendingLimitUpdate
from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError
from finance_api.schemas.pagination import PaginatedResponse


class SpendingLimitService:
    def __init__(self, repo: SpendingLimitRepository):
        self.repo = repo

    @handle_service_errors
    async def create(self, limit_data: SpendingLimitCreate):
        return await self.repo.create(limit_data)

    @handle_service_errors
    async def list(self, page: int = 1, size: int = 10):
        skip = (page - 1) * size
        items, total = await self.repo.list(skip, size)
        return PaginatedResponse.create(items, total, page, size)

    @handle_service_errors
    async def get_by_category(self, category: str):
        return await self.repo.get_by_category(category)

    @handle_service_errors
    async def get_by_id(self, limit_id: UUID):
        limit = await self.repo.get_by_id(limit_id)
        if not limit:
            raise EntityNotFoundError(f"Spending limit with id {limit_id} not found")
        return limit

    @handle_service_errors
    async def update(self, limit_id: UUID, update_data: SpendingLimitUpdate):
        updated_limit = await self.repo.update(limit_id, update_data)
        if not updated_limit:
            raise EntityNotFoundError(f"Spending limit with id {limit_id} not found")
        return updated_limit

    @handle_service_errors
    async def delete(self, limit_id: UUID):
        deleted = await self.repo.delete(limit_id)
        if not deleted:
            raise EntityNotFoundError(f"Spending limit with id {limit_id} not found")
        return True
