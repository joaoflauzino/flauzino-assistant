from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from finance_api.core.subscription_dependencies import get_subscription_service
from finance_api.main import app
from finance_api.models.subscriptions import Subscription
from finance_api.schemas.pagination import PaginatedResponse

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_subscription_service() -> MagicMock:
    service = MagicMock()
    service.create = AsyncMock()
    service.list = AsyncMock()
    service.get_by_id = AsyncMock()
    service.update = AsyncMock()
    service.delete = AsyncMock()
    return service


@pytest.fixture
async def test_client(
    mock_subscription_service: MagicMock,
) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_subscription_service] = lambda: mock_subscription_service
    try:
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                yield client
    finally:
        app.dependency_overrides.pop(get_subscription_service, None)


def make_subscription() -> Subscription:
    return Subscription(
        id=uuid4(),
        name="Streaming",
        category="servicos",
        amount=39.9,
        payment_method="c6_joao",
        payment_type="CREDIT",
        is_active=True,
        created_at=datetime.now(UTC),
    )


async def test_create_subscription_uses_injected_service(
    test_client: AsyncClient,
    mock_subscription_service: MagicMock,
) -> None:
    subscription = make_subscription()
    mock_subscription_service.create.return_value = subscription

    response = await test_client.post(
        "/subscriptions/",
        json={
            "name": subscription.name,
            "category": subscription.category,
            "amount": subscription.amount,
            "payment_method": subscription.payment_method,
            "payment_type": subscription.payment_type,
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(subscription.id)
    mock_subscription_service.create.assert_awaited_once()


async def test_list_subscriptions_forwards_query_parameters(
    test_client: AsyncClient,
    mock_subscription_service: MagicMock,
) -> None:
    subscription = make_subscription()
    mock_subscription_service.list.return_value = PaginatedResponse.create(
        [subscription], total=1, page=2, size=5
    )

    response = await test_client.get("/subscriptions/?page=2&size=5&active_only=true")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == str(subscription.id)
    mock_subscription_service.list.assert_awaited_once_with(2, 5, True)


async def test_get_subscription_forwards_id(
    test_client: AsyncClient,
    mock_subscription_service: MagicMock,
) -> None:
    subscription = make_subscription()
    mock_subscription_service.get_by_id.return_value = subscription

    response = await test_client.get(f"/subscriptions/{subscription.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(subscription.id)
    mock_subscription_service.get_by_id.assert_awaited_once_with(subscription.id)


async def test_update_subscription_forwards_payload(
    test_client: AsyncClient,
    mock_subscription_service: MagicMock,
) -> None:
    subscription = make_subscription()
    mock_subscription_service.update.return_value = subscription

    response = await test_client.patch(
        f"/subscriptions/{subscription.id}",
        json={"amount": 49.9},
    )

    assert response.status_code == 200
    assert response.json()["amount"] == 39.9
    mock_subscription_service.update.assert_awaited_once()
    assert mock_subscription_service.update.await_args.args[0] == subscription.id
    assert mock_subscription_service.update.await_args.args[1].amount == 49.9


async def test_delete_subscription_returns_no_content(
    test_client: AsyncClient,
    mock_subscription_service: MagicMock,
) -> None:
    subscription_id = uuid4()

    response = await test_client.delete(f"/subscriptions/{subscription_id}")

    assert response.status_code == 204
    mock_subscription_service.delete.assert_awaited_once_with(subscription_id)
