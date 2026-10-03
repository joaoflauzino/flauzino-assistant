from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from finance_api.core.logger import get_logger
from finance_api.models.accounts import Account
from finance_api.schemas.accounts import AccountCreate, AccountUpdate

logger = get_logger(__name__)


class AccountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, account_id: UUID) -> Optional[Account]:
        logger.debug(f"Repository: Fetching account by ID: {account_id}")
        query = (
            select(Account)
            .options(selectinload(Account.credit_cards))
            .where(Account.id == account_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> Optional[Account]:
        logger.debug(f"Repository: Fetching account by key: {key}")
        query = (
            select(Account)
            .options(selectinload(Account.credit_cards))
            .where(Account.key == key.lower())
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self, page: int = 1, size: int = 100, owner: Optional[str] = None
    ) -> tuple[Sequence[Account], int]:
        logger.debug(f"Repository: Listing accounts page={page} size={size} owner={owner}")
        offset = (page - 1) * size
        query = select(Account).options(selectinload(Account.credit_cards))
        count_query = select(Account)

        if owner:
            query = query.where(Account.owner == owner)
            count_query = count_query.where(Account.owner == owner)

        query = query.order_by(Account.name).offset(offset).limit(size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())

        return items, total

    async def create(self, account_data: AccountCreate) -> Account:
        logger.debug(f"Repository: Creating account with key: {account_data.key}")
        account = Account(
            key=account_data.key.lower(),
            name=account_data.name,
            bank=account_data.bank,
            owner=account_data.owner,
            type=account_data.type,
        )
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def update(self, account_id: UUID, update_data: AccountUpdate) -> Optional[Account]:
        logger.debug(f"Repository: Updating account: {account_id}")
        account = await self.get_by_id(account_id)
        if not account:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if "key" in update_dict and update_dict["key"]:
            update_dict["key"] = update_dict["key"].lower()

        for key, value in update_dict.items():
            setattr(account, key, value)

        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def delete(self, account_id: UUID) -> bool:
        logger.debug(f"Repository: Deleting account: {account_id}")
        account = await self.get_by_id(account_id)
        if not account:
            return False

        await self.db.delete(account)
        await self.db.commit()
        return True
