from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.payment_methods import PaymentMethod
from finance_api.schemas.payment_methods import PaymentMethodCreate, PaymentMethodUpdate
from finance_api.core.logger import get_logger

logger = get_logger(__name__)


class PaymentMethodRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, method_id: UUID) -> Optional[PaymentMethod]:
        logger.debug(f"Repository: Fetching payment method by ID: {method_id}")
        result = await self.db.execute(
            select(PaymentMethod).where(PaymentMethod.id == method_id)
        )
        method = result.scalar_one_or_none()
        if method:
            logger.debug(f"Repository: Found payment method: {method.key}")
        else:
            logger.debug(f"Repository: Payment method {method_id} not found")
        return method

    async def get_by_key(self, key: str) -> Optional[PaymentMethod]:
        logger.debug(f"Repository: Fetching payment method by key: {key}")
        result = await self.db.execute(
            select(PaymentMethod).where(PaymentMethod.key == key.lower())
        )
        method = result.scalar_one_or_none()
        if method:
            logger.debug(f"Repository: Found payment method with key: {key}")
        else:
            logger.debug(f"Repository: Payment method with key '{key}' not found")
        return method

    async def list(
        self, page: int = 1, size: int = 100
    ) -> tuple[Sequence[PaymentMethod], int]:
        logger.debug(f"Repository: Listing payment methods page={page} size={size}")
        offset = (page - 1) * size
        query = (
            select(PaymentMethod)
            .order_by(PaymentMethod.display_name)
            .offset(offset)
            .limit(size)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Count total
        # In a real app, optimize this count query
        count_query = select(PaymentMethod)
        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())

        logger.debug(f"Repository: Found {len(items)} payment methods, total={total}")
        return items, total

    async def create(self, method_data: PaymentMethodCreate) -> PaymentMethod:
        logger.debug(f"Repository: Creating payment method with key: {method_data.key}")
        method = PaymentMethod(
            key=method_data.key.lower(),
            display_name=method_data.display_name,
        )
        self.db.add(method)
        await self.db.commit()
        await self.db.refresh(method)
        logger.debug(f"Repository: Payment method created with ID: {method.id}")
        return method

    async def update(
        self, method_id: UUID, update_data: PaymentMethodUpdate
    ) -> Optional[PaymentMethod]:
        logger.debug(f"Repository: Updating payment method: {method_id}")
        method = await self.get_by_id(method_id)
        if not method:
            logger.debug(
                f"Repository: Cannot update, payment method {method_id} not found"
            )
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if "key" in update_dict and update_dict["key"]:
            update_dict["key"] = update_dict["key"].lower()

        for key, value in update_dict.items():
            setattr(method, key, value)

        await self.db.commit()
        await self.db.refresh(method)
        logger.debug(f"Repository: Payment method {method_id} updated successfully")
        return method

    async def delete(self, method_id: UUID) -> bool:
        logger.debug(f"Repository: Deleting payment method: {method_id}")
        method = await self.get_by_id(method_id)
        if not method:
            logger.debug(
                f"Repository: Cannot delete, payment method {method_id} not found"
            )
            return False

        await self.db.delete(method)
        await self.db.commit()
        logger.debug(f"Repository: Payment method {method_id} deleted successfully")
        return True
