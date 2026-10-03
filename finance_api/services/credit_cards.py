from typing import Optional, Sequence
from uuid import UUID

from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityConflictError, EntityNotFoundError
from finance_api.core.logger import get_logger
from finance_api.models.credit_cards import CreditCard
from finance_api.repositories.accounts import AccountRepository
from finance_api.repositories.credit_cards import CreditCardRepository
from finance_api.schemas.credit_cards import CreditCardCreate, CreditCardUpdate

logger = get_logger(__name__)


class CreditCardService:
    def __init__(
        self,
        repository: CreditCardRepository,
        account_repository: Optional[AccountRepository] = None,
    ):
        self.repository = repository
        self.account_repository = account_repository

    @handle_service_errors
    async def list(
        self, page: int = 1, size: int = 100, account_id: Optional[UUID] = None
    ) -> tuple[Sequence[CreditCard], int]:
        logger.info(f"Listing credit cards page={page} size={size} account_id={account_id}")
        return await self.repository.list(page, size, account_id)

    @handle_service_errors
    async def get_by_id(self, card_id: UUID) -> CreditCard:
        logger.info(f"Getting credit card by ID: {card_id}")
        card = await self.repository.get_by_id(card_id)
        if not card:
            raise EntityNotFoundError(f"Cartão de crédito com ID {card_id} não encontrado")
        return card

    @handle_service_errors
    async def get_by_key(self, key: str) -> CreditCard:
        logger.info(f"Getting credit card by key: {key}")
        card = await self.repository.get_by_key(key)
        if not card:
            raise EntityNotFoundError(f"Cartão de crédito com chave '{key}' não encontrado")
        return card

    @handle_service_errors
    async def create(self, card_data: CreditCardCreate) -> CreditCard:
        logger.info(f"Creating credit card: {card_data.key}")
        if self.account_repository:
            account = await self.account_repository.get_by_id(card_data.account_id)
            if not account:
                raise EntityNotFoundError(
                    f"Conta vinculada com ID {card_data.account_id} não encontrada"
                )

        existing = await self.repository.get_by_key(card_data.key)
        if existing:
            raise EntityConflictError(f"Cartão de crédito com chave '{card_data.key}' já existe.")

        return await self.repository.create(card_data)

    @handle_service_errors
    async def update(self, card_id: UUID, update_data: CreditCardUpdate) -> CreditCard:
        logger.info(f"Updating credit card: {card_id}")
        if update_data.account_id and self.account_repository:
            account = await self.account_repository.get_by_id(update_data.account_id)
            if not account:
                raise EntityNotFoundError(
                    f"Conta vinculada com ID {update_data.account_id} não encontrada"
                )

        if update_data.key:
            existing = await self.repository.get_by_key(update_data.key)
            if existing and existing.id != card_id:
                raise EntityConflictError(
                    f"Cartão de crédito com chave '{update_data.key}' já existe."
                )

        card = await self.repository.update(card_id, update_data)
        if not card:
            raise EntityNotFoundError(f"Cartão de crédito com ID {card_id} não encontrado")
        return card

    @handle_service_errors
    async def delete(self, card_id: UUID) -> None:
        logger.info(f"Deleting credit card: {card_id}")
        success = await self.repository.delete(card_id)
        if not success:
            raise EntityNotFoundError(f"Cartão de crédito com ID {card_id} não encontrado")
