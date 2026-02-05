from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.payment_owners import PaymentOwner
from finance_api.schemas.payment_owners import PaymentOwnerCreate, PaymentOwnerUpdate


class PaymentOwnerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, owner_id: UUID) -> Optional[PaymentOwner]:
        result = await self.db.execute(select(PaymentOwner).where(PaymentOwner.id == owner_id))
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> Optional[PaymentOwner]:
        result = await self.db.execute(
            select(PaymentOwner).where(PaymentOwner.key == key.lower())
        )
        return result.scalar_one_or_none()

    async def list(self, page: int = 1, size: int = 100) -> tuple[Sequence[PaymentOwner], int]:
        offset = (page - 1) * size
        query = select(PaymentOwner).order_by(PaymentOwner.display_name).offset(offset).limit(size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Count total
        count_query = select(PaymentOwner)
        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())

        return items, total

    async def create(self, owner_data: PaymentOwnerCreate) -> PaymentOwner:
        owner = PaymentOwner(
            key=owner_data.key.lower(),
            display_name=owner_data.display_name,
        )
        self.db.add(owner)
        await self.db.commit()
        await self.db.refresh(owner)
        return owner

    async def update(
        self, owner_id: UUID, update_data: PaymentOwnerUpdate
    ) -> Optional[PaymentOwner]:
        owner = await self.get_by_id(owner_id)
        if not owner:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if "key" in update_dict and update_dict["key"]:
            update_dict["key"] = update_dict["key"].lower()

        for key, value in update_dict.items():
            setattr(owner, key, value)

        await self.db.commit()
        await self.db.refresh(owner)
        return owner

    async def delete(self, owner_id: UUID) -> bool:
        owner = await self.get_by_id(owner_id)
        if not owner:
            return False

        await self.db.delete(owner)
        await self.db.commit()
        return True
