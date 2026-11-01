from collections.abc import Sequence
from uuid import UUID, uuid4

from finance_api.models.accounts import Account
from finance_api.schemas.accounts import AccountCreate, AccountUpdate


class InMemoryAccountRepository:
    """Fast in-memory implementation of AccountRepositoryProtocol for unit tests.

    No inheritance needed: verified against AccountRepositoryProtocol via structural subtyping.
    """

    def __init__(self) -> None:
        self._store: dict[UUID, Account] = {}

    async def get_by_id(self, entity_id: UUID) -> Account | None:
        return self._store.get(entity_id)

    async def get_by_key(self, key: str) -> Account | None:
        target = key.lower()
        for acc in self._store.values():
            if acc.key == target:
                return acc
        return None

    async def list(
        self,
        page: int = 1,
        size: int = 100,
        owner: str | None = None,
    ) -> tuple[Sequence[Account], int]:
        items = list(self._store.values())
        if owner:
            items = [a for a in items if a.owner == owner]
        items.sort(key=lambda a: a.name or "")
        total = len(items)
        offset = (page - 1) * size
        return items[offset : offset + size], total

    async def create(self, account_data: AccountCreate) -> Account:
        acc_id = uuid4()
        account = Account(
            id=acc_id,
            key=account_data.key.lower(),
            name=account_data.name,
            bank=account_data.bank,
            owner=account_data.owner,
            type=account_data.type,
        )
        self._store[acc_id] = account
        return account

    async def update(self, account_id: UUID, update_data: AccountUpdate) -> Account | None:
        account = self._store.get(account_id)
        if not account:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if "key" in update_dict and update_dict["key"]:
            update_dict["key"] = update_dict["key"].lower()

        for field, value in update_dict.items():
            setattr(account, field, value)

        return account

    async def delete(self, account_id: UUID) -> bool:
        removed = self._store.pop(account_id, None)
        return removed is not None
