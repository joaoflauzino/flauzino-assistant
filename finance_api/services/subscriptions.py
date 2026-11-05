from uuid import UUID

from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.core.logger import get_logger
from finance_api.models.subscriptions import Subscription
from finance_api.repositories.protocols import (
    CategoryRepositoryProtocol,
    SubscriptionRepositoryProtocol,
)
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.schemas.subscriptions import SubscriptionCreate, SubscriptionUpdate
from finance_api.services.payment_resolution import PaymentResolutionService
from finance_api.services.update_preparation import (
    ExpenseCategoryStep,
    SubscriptionPaymentStep,
    UpdateDataPreparer,
)

logger = get_logger(__name__)


class SubscriptionService:
    def __init__(
        self,
        repo: SubscriptionRepositoryProtocol,
        *,
        payment_resolver: PaymentResolutionService,
        category_repo: CategoryRepositoryProtocol,
    ):
        self.repo = repo
        self.payment_resolver = payment_resolver
        self.category_repo = category_repo

    async def _resolve_payment_relations(
        self, data: SubscriptionCreate | SubscriptionUpdate
    ) -> None:
        if not data.payment_method:
            return

        target = await self.payment_resolver.resolve(
            data.payment_method,
            requested_payment_type=data.payment_type,
        )
        if target.credit_card_id:
            data.credit_card_id = target.credit_card_id
        if target.account_id:
            data.account_id = target.account_id
        data.payment_type = target.payment_type

    @handle_service_errors
    async def create(self, subscription: SubscriptionCreate) -> "Subscription":
        logger.info(f"Creating subscription: {subscription.name} - {subscription.category}")

        if not await self.category_repo.get_by_key(subscription.category):
            raise ValidationError(
                f"Categoria '{subscription.category}' não existe. Por favor, crie-a primeiro."
            )

        await self._resolve_payment_relations(subscription)
        return await self.repo.create(subscription)

    @handle_service_errors
    async def list(
        self, page: int = 1, size: int = 10, active_only: bool = False
    ) -> PaginatedResponse["Subscription"]:
        logger.info(f"Listing subscriptions page {page} size {size} active_only {active_only}")
        skip = (page - 1) * size
        items, total = await self.repo.list(skip, size, active_only)
        return PaginatedResponse.create(list(items), total, page, size)

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

        await self._build_update_preparer().prepare(update_data)

        current_subscription = await self.repo.get_by_id(subscription_id)
        if not current_subscription:
            raise EntityNotFoundError(f"Assinatura com ID {subscription_id} não encontrada")

        updated_subscription = await self.repo.update(subscription_id, update_data)
        if not updated_subscription:
            raise EntityNotFoundError(f"Assinatura com ID {subscription_id} não encontrada")
        return updated_subscription

    def _build_update_preparer(self) -> UpdateDataPreparer[SubscriptionUpdate]:
        """Builds the category/payment preparation chain used before persisting an update."""
        return UpdateDataPreparer(
            (
                ExpenseCategoryStep(self.category_repo),
                SubscriptionPaymentStep(self.payment_resolver),
            )
        )

    @handle_service_errors
    async def delete(self, subscription_id: UUID) -> bool:
        logger.info(f"Deleting subscription: {subscription_id}")
        deleted = await self.repo.delete(subscription_id)
        if not deleted:
            raise EntityNotFoundError(f"Assinatura com ID {subscription_id} não encontrada")
        return True
