from uuid import UUID

from finance_api.models.subscriptions import Subscription

from finance_api.repositories.subscriptions import SubscriptionRepository
from finance_api.repositories.categories import CategoryRepository
from finance_api.schemas.subscriptions import SubscriptionCreate, SubscriptionUpdate
from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.core.logger import get_logger

logger = get_logger(__name__)


class SubscriptionService:
    def __init__(self, repo: SubscriptionRepository):
        self.repo = repo

    @handle_service_errors
    async def create(self, subscription: SubscriptionCreate) -> "Subscription":
        logger.info(f"Creating subscription: {subscription.name} - {subscription.category}")

        category_repo = CategoryRepository(self.repo.db)
        if not await category_repo.get_by_key(subscription.category):
            raise ValidationError(
                f"Categoria '{subscription.category}' não existe. Por favor, crie-a primeiro."
            )

        return await self.repo.create(subscription)

    @handle_service_errors
    async def list(
        self, page: int = 1, size: int = 10, active_only: bool = False
    ) -> PaginatedResponse["Subscription"]:
        logger.info(f"Listing subscriptions page {page} size {size} active_only {active_only}")
        skip = (page - 1) * size
        items, total = await self.repo.list(skip, size, active_only)
        return PaginatedResponse.create(items, total, page, size)

    @handle_service_errors
    async def get_by_id(self, subscription_id: UUID) -> "Subscription":
        logger.info(f"Getting subscription by id: {subscription_id}")
        subscription = await self.repo.get_by_id(subscription_id)
        if not subscription:
            raise EntityNotFoundError(f"Assinatura com ID {subscription_id} não encontrada")
        return subscription

    @handle_service_errors
    async def update(
        self, subscription_id: UUID, update_data: SubscriptionUpdate
    ) -> "Subscription":
        logger.info(f"Updating subscription: {subscription_id}")

        if update_data.category:
            category_repo = CategoryRepository(self.repo.db)
            if not await category_repo.get_by_key(update_data.category):
                raise ValidationError(
                    f"Categoria '{update_data.category}' não existe. Por favor, crie-a primeiro."
                )

        current_subscription = await self.repo.get_by_id(subscription_id)
        if not current_subscription:
            raise EntityNotFoundError(f"Assinatura com ID {subscription_id} não encontrada")

        updated_subscription = await self.repo.update(subscription_id, update_data)
        if not updated_subscription:
            raise EntityNotFoundError(f"Assinatura com ID {subscription_id} não encontrada")
        return updated_subscription

    @handle_service_errors
    async def delete(self, subscription_id: UUID) -> bool:
        logger.info(f"Deleting subscription: {subscription_id}")
        deleted = await self.repo.delete(subscription_id)
        if not deleted:
            raise EntityNotFoundError(f"Assinatura com ID {subscription_id} não encontrada")
        return True
