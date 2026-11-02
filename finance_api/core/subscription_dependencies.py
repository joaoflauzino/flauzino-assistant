"""FastAPI dependency providers for subscription services."""

from typing import Annotated

from fastapi import Depends

from finance_api.core.dependencies import DBSessionDep
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.subscriptions import SubscriptionRepository
from finance_api.services.payment_resolution import PaymentResolutionService
from finance_api.services.subscriptions import SubscriptionService


def get_subscription_service(db: DBSessionDep) -> SubscriptionService:
    """Builds the subscription service with its persistence collaborators injected."""
    return SubscriptionService(
        repo=SubscriptionRepository(db),
        payment_resolver=PaymentResolutionService(db=db),
        category_repo=CategoryRepository(db),
    )


SubscriptionServiceDep = Annotated[
    SubscriptionService,
    Depends(get_subscription_service),
]
