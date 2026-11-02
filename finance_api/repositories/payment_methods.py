from collections.abc import Awaitable, Callable, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.logger import get_logger
from finance_api.models.accounts import Account
from finance_api.models.credit_cards import CreditCard
from finance_api.models.payment_methods import PaymentMethod
from finance_api.schemas.payment_methods import PaymentMethodCreate, PaymentMethodUpdate

logger = get_logger(__name__)

type PaymentLookup = Callable[[str], Awaitable[PaymentMethod | None]]


def payment_method_from_credit_card(card: CreditCard) -> PaymentMethod:
    """Adapts a credit card to the payment-method contract consumed by services."""
    return PaymentMethod(
        id=card.id,
        key=card.key,
        display_name=card.name,
        is_credit_card=True,
        closing_day=card.closing_day,
        due_day=card.due_day,
    )


def payment_method_from_account(account: Account, *, include_bank: bool = False) -> PaymentMethod:
    """Adapts a bank account to the payment-method contract, optionally naming the bank."""
    display_name = account.name
    if include_bank and account.bank:
        display_name = f"{account.name} ({account.bank})"

    return PaymentMethod(
        id=account.id,
        key=account.key,
        display_name=display_name,
        is_credit_card=False,
    )


class PaymentMethodRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, method_id: UUID) -> PaymentMethod | None:
        logger.debug(f"Repository: Fetching payment method by ID: {method_id}")
        result = await self.db.execute(select(PaymentMethod).where(PaymentMethod.id == method_id))
        method = result.scalar_one_or_none()
        if method:
            logger.debug(f"Repository: Found payment method: {method.key}")
        else:
            logger.debug(f"Repository: Payment method {method_id} not found")
        return method

    async def get_by_key(self, key: str) -> PaymentMethod | None:
        """Resolves a key against payment methods, credit cards and accounts, in this order."""
        logger.debug(f"Repository: Fetching payment method by key: {key}")
        normalized_key = key.lower()

        for lookup in (self._find_payment_method, self._find_credit_card, self._find_account):
            method = await lookup(normalized_key)
            if method is not None:
                return method

        logger.debug(f"Repository: Payment method with key '{key}' not found")
        return None

    async def list(self, page: int = 1, size: int = 100) -> tuple[Sequence[PaymentMethod], int]:
        logger.debug(f"Repository: Listing payment methods page={page} size={size}")
        derived = await self._list_derived_payment_methods()
        if derived:
            offset = (page - 1) * size
            return derived[offset : offset + size], len(derived)

        return await self._list_stored_payment_methods(page, size)

    async def list_credit_cards(self) -> Sequence[PaymentMethod]:
        logger.debug("Repository: Listing credit cards")
        cards = await self._list_credit_cards()
        if cards:
            return [payment_method_from_credit_card(card) for card in cards]
        return await self._list_stored_credit_cards()

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
    ) -> PaymentMethod | None:
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

    async def _find_payment_method(self, key: str) -> PaymentMethod | None:
        result = await self.db.execute(select(PaymentMethod).where(PaymentMethod.key == key))
        method = result.scalar_one_or_none()
        if method is not None:
            logger.debug(f"Repository: Found payment method: {method.key}")
        return method

    async def _find_credit_card(self, key: str) -> PaymentMethod | None:
        result = await self.db.execute(select(CreditCard).where(CreditCard.key == key))
        card = result.scalar_one_or_none()
        if card is None:
            return None

        logger.debug(f"Repository: Found credit card as payment method: {card.key}")
        return payment_method_from_credit_card(card)

    async def _find_account(self, key: str) -> PaymentMethod | None:
        result = await self.db.execute(select(Account).where(Account.key == key))
        account = result.scalar_one_or_none()
        if account is None:
            return None

        logger.debug(f"Repository: Found account as payment method: {account.key}")
        return payment_method_from_account(account)

    async def _list_derived_payment_methods(self) -> Sequence[PaymentMethod]:
        cards = await self._list_credit_cards()
        accounts = await self._list_accounts()
        return [payment_method_from_credit_card(card) for card in cards] + [
            payment_method_from_account(account, include_bank=True) for account in accounts
        ]

    async def _list_credit_cards(self) -> Sequence[CreditCard]:
        result = await self.db.execute(select(CreditCard).order_by(CreditCard.name))
        return result.scalars().all()

    async def _list_accounts(self) -> Sequence[Account]:
        result = await self.db.execute(select(Account).order_by(Account.name))
        return result.scalars().all()

    async def _list_stored_payment_methods(
        self, page: int, size: int
    ) -> tuple[Sequence[PaymentMethod], int]:
        offset = (page - 1) * size
        query = (
            select(PaymentMethod).order_by(PaymentMethod.display_name).offset(offset).limit(size)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()

        total_result = await self.db.execute(select(PaymentMethod))
        total = len(total_result.scalars().all())

        logger.debug(f"Repository: Found {len(items)} payment methods, total={total}")
        return items, total

    async def _list_stored_credit_cards(self) -> Sequence[PaymentMethod]:
        query = (
            select(PaymentMethod)
            .where(PaymentMethod.is_credit_card.is_(True))
            .order_by(PaymentMethod.display_name)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()
        logger.debug(f"Repository: Found {len(items)} credit cards")
        return items
