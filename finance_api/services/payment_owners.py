from typing import Optional, Sequence
from uuid import UUID

from finance_api.core.decorators import handle_payment_owner_errors
from finance_api.core.exceptions import EntityConflictError, EntityNotFoundError
from finance_api.core.logger import get_logger
from finance_api.repositories.payment_owners import PaymentOwnerRepository
from finance_api.models.payment_owners import PaymentOwner
from finance_api.schemas.payment_owners import PaymentOwnerCreate, PaymentOwnerUpdate

logger = get_logger(__name__)


class PaymentOwnerService:
    def __init__(self, repository: PaymentOwnerRepository):
        self.repository = repository

    @handle_payment_owner_errors
    async def list(self, page: int = 1, size: int = 100) -> tuple[Sequence[PaymentOwner], int]:
        logger.info(f"Listing payment owners page {page} size {size}")
        return await self.repository.list(page, size)

    @handle_payment_owner_errors
    async def get_by_id(self, owner_id: UUID) -> PaymentOwner:
        logger.info(f"Getting payment owner: {owner_id}")
        owner = await self.repository.get_by_id(owner_id)
        if not owner:
            raise EntityNotFoundError(f"Payment owner with ID {owner_id} not found")
        return owner

    @handle_payment_owner_errors
    async def create(self, owner_data: PaymentOwnerCreate) -> PaymentOwner:
        logger.info(f"Creating payment owner: {owner_data.key}")
        # Check if key already exists
        existing = await self.repository.get_by_key(owner_data.key)
        if existing:
            raise EntityConflictError(f"Payment owner with key '{owner_data.key}' already exists.")
        
        return await self.repository.create(owner_data)

    @handle_payment_owner_errors
    async def update(
        self, owner_id: UUID, update_data: PaymentOwnerUpdate
    ) -> PaymentOwner:
        logger.info(f"Updating payment owner: {owner_id}")
        if update_data.key:
            existing = await self.repository.get_by_key(update_data.key)
            if existing and existing.id != owner_id:
                raise EntityConflictError(f"Payment owner with key '{update_data.key}' already exists.")

        owner = await self.repository.update(owner_id, update_data)
        if not owner:
            raise EntityNotFoundError(f"Payment owner with ID {owner_id} not found")
        return owner

    @handle_payment_owner_errors
    async def delete(self, owner_id: UUID) -> None:
        logger.info(f"Deleting payment owner: {owner_id}")
        success = await self.repository.delete(owner_id)
        if not success:
            raise EntityNotFoundError(f"Payment owner with ID {owner_id} not found")
