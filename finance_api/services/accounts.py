from typing import Optional, Sequence
from uuid import UUID

from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityConflictError, EntityNotFoundError
from finance_api.core.logger import get_logger
from finance_api.models.accounts import Account
from finance_api.repositories.accounts import AccountRepository
from finance_api.schemas.accounts import AccountCreate, AccountUpdate

logger = get_logger(__name__)


class AccountService:
    def __init__(self, repository: AccountRepository):
        self.repository = repository

    @handle_service_errors
    async def list(
        self, page: int = 1, size: int = 100, owner: Optional[str] = None
    ) -> tuple[Sequence[Account], int]:
        logger.info(f"Listing accounts page={page} size={size} owner={owner}")
        return await self.repository.list(page, size, owner)

    @handle_service_errors
    async def get_by_id(self, account_id: UUID) -> Account:
        logger.info(f"Getting account by ID: {account_id}")
        account = await self.repository.get_by_id(account_id)
        if not account:
            raise EntityNotFoundError(f"Conta com ID {account_id} não encontrada")
        return account

    @handle_service_errors
    async def get_by_key(self, key: str) -> Account:
        logger.info(f"Getting account by key: {key}")
        account = await self.repository.get_by_key(key)
        if not account:
            raise EntityNotFoundError(f"Conta com chave '{key}' não encontrada")
        return account

    @handle_service_errors
    async def create(self, account_data: AccountCreate) -> Account:
        logger.info(f"Creating account: {account_data.key}")
        existing = await self.repository.get_by_key(account_data.key)
        if existing:
            raise EntityConflictError(f"Conta com chave '{account_data.key}' já existe.")

        return await self.repository.create(account_data)

    @handle_service_errors
    async def update(self, account_id: UUID, update_data: AccountUpdate) -> Account:
        logger.info(f"Updating account: {account_id}")
        if update_data.key:
            existing = await self.repository.get_by_key(update_data.key)
            if existing and existing.id != account_id:
                raise EntityConflictError(f"Conta com chave '{update_data.key}' já existe.")

        account = await self.repository.update(account_id, update_data)
        if not account:
            raise EntityNotFoundError(f"Conta com ID {account_id} não encontrada")
        return account

    @handle_service_errors
    async def delete(self, account_id: UUID) -> None:
        logger.info(f"Deleting account: {account_id}")
        success = await self.repository.delete(account_id)
        if not success:
            raise EntityNotFoundError(f"Conta com ID {account_id} não encontrada")
