from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from finance_api.core.logger import get_logger
from finance_api.models.credit_cards import CreditCard
from finance_api.schemas.credit_cards import CreditCardCreate, CreditCardUpdate

logger = get_logger(__name__)


class CreditCardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, card_id: UUID) -> Optional[CreditCard]:
        logger.debug(f"Repository: Fetching credit card by ID: {card_id}")
        query = (
            select(CreditCard)
            .options(selectinload(CreditCard.account))
            .where(CreditCard.id == card_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> Optional[CreditCard]:
        logger.debug(f"Repository: Fetching credit card by key: {key}")
        query = (
            select(CreditCard)
            .options(selectinload(CreditCard.account))
            .where(CreditCard.key == key.lower())
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self, page: int = 1, size: int = 100, account_id: Optional[UUID] = None
    ) -> tuple[Sequence[CreditCard], int]:
        logger.debug(
            f"Repository: Listing credit cards page={page} size={size} account_id={account_id}"
        )
        offset = (page - 1) * size
        query = select(CreditCard).options(selectinload(CreditCard.account))
        count_query = select(CreditCard)

        if account_id:
            query = query.where(CreditCard.account_id == account_id)
            count_query = count_query.where(CreditCard.account_id == account_id)

        query = query.order_by(CreditCard.name).offset(offset).limit(size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())

        return items, total

    async def create(self, card_data: CreditCardCreate) -> CreditCard:
        logger.debug(f"Repository: Creating credit card with key: {card_data.key}")
        card = CreditCard(
            key=card_data.key.lower(),
            name=card_data.name,
            account_id=card_data.account_id,
            closing_day=card_data.closing_day,
            due_day=card_data.due_day,
            credit_limit=card_data.credit_limit,
        )
        self.db.add(card)
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def update(self, card_id: UUID, update_data: CreditCardUpdate) -> Optional[CreditCard]:
        logger.debug(f"Repository: Updating credit card: {card_id}")
        card = await self.get_by_id(card_id)
        if not card:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if "key" in update_dict and update_dict["key"]:
            update_dict["key"] = update_dict["key"].lower()

        for key, value in update_dict.items():
            setattr(card, key, value)

        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def delete(self, card_id: UUID) -> bool:
        logger.debug(f"Repository: Deleting credit card: {card_id}")
        card = await self.get_by_id(card_id)
        if not card:
            return False

        await self.db.delete(card)
        await self.db.commit()
        return True
