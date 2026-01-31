from typing import List, Optional

from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.limits import SpendingLimit
from finance_api.schemas.limits import SpendingLimitCreate, SpendingLimitUpdate


class SpendingLimitRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, limit_data: SpendingLimitCreate) -> SpendingLimit:
        new_limit = SpendingLimit(**limit_data.model_dump())
        self.db.add(new_limit)
        await self.db.commit()
        await self.db.refresh(new_limit)
        return new_limit

    async def list(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[List[SpendingLimit], int]:
        count_query = select(func.count()).select_from(SpendingLimit)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = select(SpendingLimit).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_category(self, category: str) -> Optional[SpendingLimit]:
        result = await self.db.execute(
            select(SpendingLimit).where(SpendingLimit.category == category)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, limit_id: UUID) -> Optional[SpendingLimit]:
        result = await self.db.execute(
            select(SpendingLimit).where(SpendingLimit.id == limit_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, limit_id: UUID, update_data: SpendingLimitUpdate
    ) -> Optional[SpendingLimit]:
        stmt = (
            update(SpendingLimit)
            .where(SpendingLimit.id == limit_id)
            .values(**update_data.model_dump(exclude_unset=True))
            .returning(SpendingLimit)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def delete(self, limit_id: UUID) -> bool:
        stmt = delete(SpendingLimit).where(SpendingLimit.id == limit_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0
