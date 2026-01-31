from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from finance_api.models.spents import Spent

from finance_api.repositories.spents import SpentRepository
from finance_api.schemas.spents import SpentCreate, SpentUpdate
from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError
from finance_api.schemas.pagination import PaginatedResponse


class SpentService:
    def __init__(self, repo: SpentRepository):
        self.repo = repo

    @handle_service_errors
    async def create(self, spent: SpentCreate) -> "Spent":
        return await self.repo.create(spent)

    @handle_service_errors
    async def list(self, page: int = 1, size: int = 10) -> PaginatedResponse["Spent"]:
        skip = (page - 1) * size
        items, total = await self.repo.list(skip, size)
        return PaginatedResponse.create(items, total, page, size)

    @handle_service_errors
    async def get_by_id(self, spent_id: UUID) -> "Spent":
        spent = await self.repo.get_by_id(spent_id)
        if not spent:
            raise EntityNotFoundError(f"Spent with id {spent_id} not found")
        return spent

    @handle_service_errors
    async def update(self, spent_id: UUID, update_data: SpentUpdate) -> "Spent":
        updated_spent = await self.repo.update(spent_id, update_data)
        if not updated_spent:
            raise EntityNotFoundError(f"Spent with id {spent_id} not found")
        return updated_spent

    @handle_service_errors
    async def delete(self, spent_id: UUID) -> bool:
        deleted = await self.repo.delete(spent_id)
        if not deleted:
            raise EntityNotFoundError(f"Spent with id {spent_id} not found")
        return True
