from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.payment_methods import PaymentMethod
from finance_api.schemas.payment_methods import PaymentMethodCreate, PaymentMethodUpdate


class PaymentMethodRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, method_id: UUID) -> Optional[PaymentMethod]:
        result = await self.db.execute(select(PaymentMethod).where(PaymentMethod.id == method_id))
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> Optional[PaymentMethod]:
        result = await self.db.execute(
            select(PaymentMethod).where(PaymentMethod.key == key.lower())
        )
        return result.scalar_one_or_none()

    async def list(self, page: int = 1, size: int = 100) -> tuple[Sequence[PaymentMethod], int]:
        offset = (page - 1) * size
        query = select(PaymentMethod).order_by(PaymentMethod.display_name).offset(offset).limit(size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Count total
        # In a real app, optimize this count query
        count_query = select(PaymentMethod)
        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())

        return items, total

    async def create(self, method_data: PaymentMethodCreate) -> PaymentMethod:
        method = PaymentMethod(
            key=method_data.key.lower(),
            display_name=method_data.display_name,
        )
        self.db.add(method)
        await self.db.commit()
        await self.db.refresh(method)
        return method

    async def update(
        self, method_id: UUID, update_data: PaymentMethodUpdate
    ) -> Optional[PaymentMethod]:
        method = await self.get_by_id(method_id)
        if not method:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if "key" in update_dict and update_dict["key"]:
            update_dict["key"] = update_dict["key"].lower()

        for key, value in update_dict.items():
            setattr(method, key, value)

        await self.db.commit()
        await self.db.refresh(method)
        return method

    async def delete(self, method_id: UUID) -> bool:
        method = await self.get_by_id(method_id)
        if not method:
            return False

        await self.db.delete(method)
        await self.db.commit()
        return True
