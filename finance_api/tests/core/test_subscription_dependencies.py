from unittest.mock import AsyncMock

from finance_api.core.subscription_dependencies import get_subscription_service
from finance_api.services.subscriptions import SubscriptionService


def test_get_subscription_service_injects_all_collaborators(mocker) -> None:
    repository = mocker.MagicMock()
    category_repo = mocker.MagicMock()
    payment_resolver = mocker.MagicMock()

    service = get_subscription_service(
        repo=repository,
        category_repo=category_repo,
        payment_resolver=payment_resolver,
    )

    assert isinstance(service, SubscriptionService)
    assert service.repo is repository
    assert service.payment_resolver is payment_resolver
    assert service.category_repo is category_repo


def test_get_subscription_repository_wraps_session(mocker) -> None:
    db = AsyncMock()
    repository_factory = mocker.patch(
        "finance_api.core.subscription_dependencies.SubscriptionRepository"
    )

    from finance_api.core.subscription_dependencies import get_subscription_repository

    repository = get_subscription_repository(db)

    assert repository is repository_factory.return_value
    repository_factory.assert_called_once_with(db)
