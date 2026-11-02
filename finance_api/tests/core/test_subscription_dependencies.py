from unittest.mock import AsyncMock

from finance_api.core.subscription_dependencies import get_subscription_service
from finance_api.services.subscriptions import SubscriptionService


def test_get_subscription_service_injects_all_collaborators(mocker) -> None:
    db = AsyncMock()
    repository_factory = mocker.patch(
        "finance_api.core.subscription_dependencies.SubscriptionRepository"
    )
    payment_resolver_factory = mocker.patch(
        "finance_api.core.subscription_dependencies.PaymentResolutionService"
    )
    category_repository_factory = mocker.patch(
        "finance_api.core.subscription_dependencies.CategoryRepository"
    )

    service = get_subscription_service(db)

    assert isinstance(service, SubscriptionService)
    assert service.repo is repository_factory.return_value
    assert service.payment_resolver is payment_resolver_factory.return_value
    assert service.category_repo is category_repository_factory.return_value
    repository_factory.assert_called_once_with(db)
    payment_resolver_factory.assert_called_once_with(db=db)
    category_repository_factory.assert_called_once_with(db)
