from datetime import date
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.logger import get_logger
from finance_api.models.limits import SpendingLimit
from finance_api.schemas.limits import SpendingLimitCreate, SpendingLimitUpdate

logger = get_logger(__name__)


class SpendingLimitRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, limit_data: SpendingLimitCreate) -> SpendingLimit:
        new_limit = SpendingLimit(**limit_data.model_dump())
        self.db.add(new_limit)
        await self.db.commit()
        await self.db.refresh(new_limit)
        logger.info(f"Created spending limit: {new_limit.id}")
        return new_limit

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[SpendingLimit], int]:
        query = select(SpendingLimit)

        # Note: SpendingLimit doesn't have created_at field currently
        # If you add it later, uncomment and update this:
        # if start_date:
        #     query = query.where(
        #         func.date(func.timezone('America/Sao_Paulo', SpendingLimit.created_at)) >= start_date
        #     )
        # if end_date:
        #     query = query.where(
        #         func.date(func.timezone('America/Sao_Paulo', SpendingLimit.created_at)) <= end_date
        #     )

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        logger.info(f"Listed {len(items)} spending limits")
        return items, total

    async def get_by_category(self, category: str) -> SpendingLimit | None:
        result = await self.db.execute(
            select(SpendingLimit).where(SpendingLimit.category == category)
        )
        limit = result.scalar_one_or_none()
        if limit:
            logger.info(f"Retrieved limit for category: {category}")
        return limit

    async def get_by_id(self, limit_id: UUID) -> SpendingLimit | None:
        result = await self.db.execute(select(SpendingLimit).where(SpendingLimit.id == limit_id))
        limit = result.scalar_one_or_none()
        if limit:
            logger.info(f"Retrieved limit: {limit_id}")
        return limit

    async def update(
        self, limit_id: UUID, update_data: SpendingLimitUpdate
    ) -> SpendingLimit | None:
        stmt = (
            update(SpendingLimit)
            .where(SpendingLimit.id == limit_id)
            .values(**update_data.model_dump(exclude_unset=True))
            .returning(SpendingLimit)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        logger.info(f"Updated spending limit: {limit_id}")
        return result.scalar_one_or_none()

    async def delete(self, limit_id: UUID) -> bool:
        stmt = delete(SpendingLimit).where(SpendingLimit.id == limit_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        if result.rowcount > 0:
            logger.info(f"Deleted spending limit: {limit_id}")
        return result.rowcount > 0
