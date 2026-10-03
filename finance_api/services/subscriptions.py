from uuid import UUID

from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.core.logger import get_logger
from finance_api.models.subscriptions import Subscription
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.subscriptions import SubscriptionRepository
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.schemas.subscriptions import SubscriptionCreate, SubscriptionUpdate

logger = get_logger(__name__)


class SubscriptionService:
    def __init__(self, repo: SubscriptionRepository):
        self.repo = repo

    async def _resolve_payment_relations(
        self, data: SubscriptionCreate | SubscriptionUpdate
    ) -> None:
        if not data.payment_method:
            return

        from sqlalchemy import select
        from finance_api.models.accounts import Account
        from finance_api.models.credit_cards import CreditCard

        try:
            card_res = await self.repo.db.execute(
                select(CreditCard).where(CreditCard.key == data.payment_method.lower())
            )
            card = card_res.scalar_one_or_none()
            if card:
                data.credit_card_id = card.id
                data.account_id = card.account_id
                data.payment_type = "CREDIT"
                return
        except Exception as e:
            logger.debug(f"Could not resolve credit card for subscription: {e}")

        try:
            acc_res = await self.repo.db.execute(
                select(Account).where(Account.key == data.payment_method.lower())
            )
            acc = acc_res.scalar_one_or_none()
            if acc:
                data.account_id = acc.id
                if not getattr(data, "payment_type", None) or data.payment_type == "CREDIT":
                    data.payment_type = "DEBIT"
                return
        except Exception as e:
            logger.debug(f"Could not resolve account for subscription: {e}")

    @handle_service_errors
    async def create(self, subscription: SubscriptionCreate) -> "Subscription":
        logger.info(f"Creating subscription: {subscription.name} - {subscription.category}")

        category_repo = CategoryRepository(self.repo.db)
        if not await category_repo.get_by_key(subscription.category):
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

        if update_data.payment_method:
            await self._resolve_payment_relations(update_data)

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
