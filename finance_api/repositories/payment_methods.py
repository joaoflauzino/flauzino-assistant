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
        result = await self.db.execute(select(PaymentMethod).where(PaymentMethod.id == method_id))
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
            logger.debug(f"Repository: Found payment method: {method.key}")
            return method

        # Check credit_cards table
        try:
            from finance_api.models.credit_cards import CreditCard

            card_res = await self.db.execute(
                select(CreditCard).where(CreditCard.key == key.lower())
            )
            card = card_res.scalar_one_or_none()
            if card:
                logger.debug(f"Repository: Found credit card as payment method: {card.key}")
                card_name = getattr(card, "name", None) or getattr(card, "display_name", card.key)
                return PaymentMethod(
                    id=card.id,
                    key=card.key,
                    display_name=card_name,
                    is_credit_card=True,
                    closing_day=card.closing_day,
                    due_day=card.due_day,
                )
        except Exception as e:
            logger.debug(f"Repository: Could not query credit_cards: {e}")

        # Check accounts table
        try:
            from finance_api.models.accounts import Account

            acc_res = await self.db.execute(select(Account).where(Account.key == key.lower()))
            acc = acc_res.scalar_one_or_none()
            if acc:
                logger.debug(f"Repository: Found account as payment method: {acc.key}")
                acc_name = getattr(acc, "name", None) or getattr(acc, "display_name", acc.key)
                return PaymentMethod(
                    id=acc.id,
                    key=acc.key,
                    display_name=acc_name,
                    is_credit_card=False,
                )
        except Exception as e:
            logger.debug(f"Repository: Could not query accounts: {e}")

        logger.debug(f"Repository: Payment method with key '{key}' not found")
        return None

    async def list(self, page: int = 1, size: int = 100) -> tuple[Sequence[PaymentMethod], int]:
        logger.debug(f"Repository: Listing payment methods page={page} size={size}")
        try:
            from finance_api.models.credit_cards import CreditCard
            from finance_api.models.accounts import Account

            cards_res = await self.db.execute(select(CreditCard).order_by(CreditCard.name))
            cards = cards_res.scalars().all()
            accs_res = await self.db.execute(select(Account).order_by(Account.name))
            accs = accs_res.scalars().all()

            if cards or accs:
                items: list[PaymentMethod] = []
                for c in cards:
                    card_name = getattr(c, "name", None) or getattr(c, "display_name", c.key)
                    items.append(
                        PaymentMethod(
                            id=c.id,
                            key=c.key,
                            display_name=card_name,
                            is_credit_card=True,
                            closing_day=c.closing_day,
                            due_day=c.due_day,
                        )
                    )
                for a in accs:
                    bank_info = f" ({a.bank})" if getattr(a, "bank", None) else ""
                    acc_name = (
                        getattr(a, "name", None) or getattr(a, "display_name", a.key)
                    ) + bank_info
                    items.append(
                        PaymentMethod(
                            id=a.id,
                            key=a.key,
                            display_name=acc_name,
                            is_credit_card=False,
                        )
                    )
                offset = (page - 1) * size
                return items[offset : offset + size], len(items)
        except Exception as e:
            logger.debug(f"Repository: Could not list from cards/accounts: {e}")

        offset = (page - 1) * size
        query = (
            select(PaymentMethod).order_by(PaymentMethod.display_name).offset(offset).limit(size)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()

        count_query = select(PaymentMethod)
        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())

        logger.debug(f"Repository: Found {len(items)} payment methods, total={total}")
        return items, total

    async def list_credit_cards(self) -> Sequence[PaymentMethod]:
        logger.debug("Repository: Listing credit cards")
        try:
            from finance_api.models.credit_cards import CreditCard

            result = await self.db.execute(select(CreditCard).order_by(CreditCard.name))
            cards = result.scalars().all()
            if cards:
                return [
                    PaymentMethod(
                        id=c.id,
                        key=c.key,
                        display_name=getattr(c, "name", None) or getattr(c, "display_name", c.key),
                        is_credit_card=True,
                        closing_day=c.closing_day,
                        due_day=c.due_day,
                    )
                    for c in cards
                ]
        except Exception as e:
            logger.debug(f"Repository: Could not query credit_cards: {e}")

        query = (
            select(PaymentMethod)
            .where(PaymentMethod.is_credit_card.is_(True))
            .order_by(PaymentMethod.display_name)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()
        logger.debug(f"Repository: Found {len(items)} credit cards")
        return items

    async def create(self, method_data: PaymentMethodCreate) -> PaymentMethod:
        logger.debug(f"Repository: Creating payment method with key: {method_data.key}")
        method = PaymentMethod(
            key=method_data.key.lower(),
            display_name=method_data.display_name,
            is_credit_card=method_data.is_credit_card,
            closing_day=method_data.closing_day,
            due_day=method_data.due_day,
        )
        self.db.add(method)
        await self.db.commit()
        await self.db.refresh(method)
        return method

    async def update(
        self, method_id: UUID, update_data: PaymentMethodUpdate
    ) -> Optional[PaymentMethod]:
        logger.debug(f"Repository: Updating payment method: {method_id}")
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
        logger.debug(f"Repository: Deleting payment method: {method_id}")
        method = await self.get_by_id(method_id)
        if not method:
            return False

        await self.db.delete(method)
        await self.db.commit()
        return True
