from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.spents import Spent
from finance_api.schemas.spents import SpentCreate


class SpentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, spent: SpentCreate) -> Spent:
        new_spent = Spent(**spent.model_dump())
        self.db.add(new_spent)
        await self.db.commit()
        await self.db.refresh(new_spent)
        return new_spent

    async def list(self, skip: int = 0, limit: int = 100) -> List[Spent]:
        result = await self.db.execute(select(Spent).offset(skip).limit(limit))
        return list(result.scalars().all())
