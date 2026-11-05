"""FastAPI dependency providers for subscription services."""

from typing import Annotated

from fastapi import Depends

from finance_api.core.dependencies import (
    CategoryRepoDep,
    DBSessionDep,
    PaymentResolutionServiceDep,
)
from finance_api.repositories.protocols import SubscriptionRepositoryProtocol
from finance_api.repositories.subscriptions import SubscriptionRepository
from finance_api.services.subscriptions import SubscriptionService


def get_subscription_repository(db: DBSessionDep) -> SubscriptionRepositoryProtocol:
    return SubscriptionRepository(db)


SubscriptionRepoDep = Annotated[
    SubscriptionRepositoryProtocol, Depends(get_subscription_repository)
]


def get_subscription_service(
    repo: SubscriptionRepoDep,
    category_repo: CategoryRepoDep,
    payment_resolver: PaymentResolutionServiceDep,
) -> SubscriptionService:
    """Builds the subscription service with its persistence collaborators injected."""
    return SubscriptionService(
        repo=repo,
        payment_resolver=payment_resolver,
        category_repo=category_repo,
    )


SubscriptionServiceDep = Annotated[
    SubscriptionService,
    Depends(get_subscription_service),
]
