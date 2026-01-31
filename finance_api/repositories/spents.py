from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.spents import Spent
from finance_api.schemas.spents import SpentCreate, SpentUpdate


class SpentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, spent: SpentCreate) -> Spent:
        new_spent = Spent(**spent.model_dump())
        self.db.add(new_spent)
        await self.db.commit()
        await self.db.refresh(new_spent)
        return new_spent

    async def list(self, skip: int = 0, limit: int = 100) -> tuple[List[Spent], int]:
        count_query = select(func.count()).select_from(Spent)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = select(Spent).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_id(self, spent_id: UUID) -> Optional[Spent]:
        result = await self.db.execute(select(Spent).where(Spent.id == spent_id))
        return result.scalar_one_or_none()

    async def update(self, spent_id: UUID, update_data: SpentUpdate) -> Optional[Spent]:
        stmt = (
            update(Spent)
            .where(Spent.id == spent_id)
            .values(**update_data.model_dump(exclude_unset=True))
            .returning(Spent)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def delete(self, spent_id: UUID) -> bool:
        stmt = delete(Spent).where(Spent.id == spent_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0
