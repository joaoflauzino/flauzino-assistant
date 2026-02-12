from typing import Sequence
from uuid import UUID

from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityConflictError, EntityNotFoundError
from finance_api.core.logger import get_logger
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.models.payment_methods import PaymentMethod
from finance_api.schemas.payment_methods import PaymentMethodCreate, PaymentMethodUpdate

logger = get_logger(__name__)


class PaymentMethodService:
    def __init__(self, repository: PaymentMethodRepository):
        self.repository = repository

    @handle_service_errors
    async def list(
        self, page: int = 1, size: int = 100
    ) -> tuple[Sequence[PaymentMethod], int]:
        logger.info(f"Listing payment methods page {page} size {size}")
        return await self.repository.list(page, size)

    @handle_service_errors
    async def get_by_id(self, method_id: UUID) -> PaymentMethod:
        logger.info(f"Getting payment method: {method_id}")
        method = await self.repository.get_by_id(method_id)
        if not method:
            raise EntityNotFoundError(f"Payment method with ID {method_id} not found")
        return method

    @handle_service_errors
    async def create(self, method_data: PaymentMethodCreate) -> PaymentMethod:
        logger.info(f"Creating payment method: {method_data.key}")
        # Check if key already exists
        existing = await self.repository.get_by_key(method_data.key)
        if existing:
            raise EntityConflictError(
                f"Payment method with key '{method_data.key}' already exists."
            )

        return await self.repository.create(method_data)

    @handle_service_errors
    async def update(
        self, method_id: UUID, update_data: PaymentMethodUpdate
    ) -> PaymentMethod:
        logger.info(f"Updating payment method: {method_id}")
        if update_data.key:
            existing = await self.repository.get_by_key(update_data.key)
            if existing and existing.id != method_id:
                raise EntityConflictError(
                    f"Payment method with key '{update_data.key}' already exists."
                )

        method = await self.repository.update(method_id, update_data)
        if not method:
            raise EntityNotFoundError(f"Payment method with ID {method_id} not found")
        return method

    @handle_service_errors
    async def delete(self, method_id: UUID) -> None:
        logger.info(f"Deleting payment method: {method_id}")
        success = await self.repository.delete(method_id)
        if not success:
            raise EntityNotFoundError(f"Payment method with ID {method_id} not found")
