from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.limits import SpendingLimit
from finance_api.schemas.limits import SpendingLimitCreate


class SpendingLimitRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update(self, limit_data: SpendingLimitCreate) -> SpendingLimit:
        # Check if limit for category already exists
        result = await self.db.execute(
            select(SpendingLimit).where(SpendingLimit.category == limit_data.category)
        )
        existing_limit = result.scalar_one_or_none()

        if existing_limit:
            existing_limit.amount = limit_data.amount
            await self.db.commit()
            await self.db.refresh(existing_limit)
            return existing_limit
        else:
            new_limit = SpendingLimit(**limit_data.model_dump())
            self.db.add(new_limit)
            await self.db.commit()
            await self.db.refresh(new_limit)
            return new_limit

    async def list(self) -> List[SpendingLimit]:
        result = await self.db.execute(select(SpendingLimit))
        return list(result.scalars().all())

    async def get_by_category(self, category: str) -> Optional[SpendingLimit]:
        result = await self.db.execute(
            select(SpendingLimit).where(SpendingLimit.category == category)
        )
        return result.scalar_one_or_none()
