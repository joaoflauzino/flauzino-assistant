from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.schemas.limits import SpendingLimitCreate
from finance_api.core.decorators import handle_service_errors


class SpendingLimitService:
    def __init__(self, repo: SpendingLimitRepository):
        self.repo = repo

    @handle_service_errors
    async def create_or_update(self, limit_data: SpendingLimitCreate):
        return await self.repo.create_or_update(limit_data)

    @handle_service_errors
    async def list(self):
        return await self.repo.list()

    @handle_service_errors
    async def get_by_category(self, category: str):
        return await self.repo.get_by_category(category)
