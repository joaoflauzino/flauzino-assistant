from finance_api.repositories.spents import SpentRepository
from finance_api.schemas.spents import SpentCreate
from finance_api.core.decorators import handle_service_errors


class SpentService:
    def __init__(self, repo: SpentRepository):
        self.repo = repo

    @handle_service_errors
    async def create(self, spent: SpentCreate):
        return await self.repo.create(spent)

    @handle_service_errors
    async def list(self, skip: int = 0, limit: int = 100):
        return await self.repo.list(skip, limit)
