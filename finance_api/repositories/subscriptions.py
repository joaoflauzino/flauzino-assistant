from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.subscriptions import Subscription
from finance_api.schemas.subscriptions import SubscriptionCreate, SubscriptionUpdate
from finance_api.core.logger import get_logger

logger = get_logger(__name__)


class SubscriptionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, subscription: SubscriptionCreate) -> Subscription:
        new_subscription = Subscription(**subscription.model_dump())
        self.db.add(new_subscription)
        await self.db.commit()
        await self.db.refresh(new_subscription)
        logger.info(f"Created subscription: {new_subscription.id}")
        return new_subscription

    async def list(
        self, skip: int = 0, limit: int = 100, active_only: bool = False
    ) -> tuple[List[Subscription], int]:
        query = select(Subscription)

        if active_only:
            query = query.where(Subscription.is_active)

        # Count query
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Pagination
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        logger.info(f"Listed {len(items)} subscriptions")
        return items, total

    async def get_by_id(self, subscription_id: UUID) -> Optional[Subscription]:
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if subscription:
            logger.info(f"Retrieved subscription: {subscription_id}")
        return subscription

    async def update(
        self, subscription_id: UUID, update_data: SubscriptionUpdate
    ) -> Optional[Subscription]:
        stmt = (
            update(Subscription)
            .where(Subscription.id == subscription_id)
            .values(**update_data.model_dump(exclude_unset=True))
            .returning(Subscription)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        logger.info(f"Updated subscription: {subscription_id}")
        return result.scalar_one_or_none()

    async def delete(self, subscription_id: UUID) -> bool:
        stmt = delete(Subscription).where(Subscription.id == subscription_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        if result.rowcount > 0:
            logger.info(f"Deleted subscription: {subscription_id}")
        return result.rowcount > 0
