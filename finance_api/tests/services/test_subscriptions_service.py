from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.models.subscriptions import Subscription
from finance_api.schemas.payment_resolution import ResolvedPaymentTarget
from finance_api.schemas.subscriptions import SubscriptionCreate, SubscriptionUpdate
from finance_api.services.subscriptions import SubscriptionService
from finance_api.tests.fakes.fake_payment_resolver import FakePaymentResolver

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def category_repo():
    repo = AsyncMock()
    repo.get_by_key.return_value = MagicMock(key="servicos")
    return repo


@pytest.fixture
def payment_resolver():
    return FakePaymentResolver()


async def test_create_subscription_with_credit_card(mock_repo, category_repo):
    card_id = uuid4()
    account_id = uuid4()
    resolver = FakePaymentResolver(
        {
            "itau_card_joao": ResolvedPaymentTarget(
                account_id=account_id,
                credit_card_id=card_id,
                payment_type="CREDIT",
            )
        }
    )

    sub = Subscription(
        id=uuid4(),
        name="Netflix",
        category="servicos",
        amount=55.90,
        payment_method="itau_card_joao",
        payment_type="CREDIT",
        account_id=account_id,
        credit_card_id=card_id,
    )
    mock_repo.create.return_value = sub

    service = SubscriptionService(
        repo=mock_repo,
        payment_resolver=resolver,
        category_repo=category_repo,
    )
    create_dto = SubscriptionCreate(
        name="Netflix",
        category="servicos",
        amount=55.90,
        payment_method="itau_card_joao",
    )

    created = await service.create(create_dto)
    assert created.credit_card_id == card_id
    assert created.account_id == account_id
    assert created.payment_type == "CREDIT"
    assert create_dto.credit_card_id == card_id
    assert create_dto.account_id == account_id


async def test_create_subscription_with_account(mock_repo, category_repo):
    account_id = uuid4()
    resolver = FakePaymentResolver(
        {
            "nubank_joao": ResolvedPaymentTarget(
                account_id=account_id,
                credit_card_id=None,
                payment_type="DEBIT",
            )
        }
    )

    sub = Subscription(
        id=uuid4(),
        name="Spotify",
        category="servicos",
        amount=21.90,
        payment_method="nubank_joao",
        payment_type="DEBIT",
        account_id=account_id,
    )
    mock_repo.create.return_value = sub

    service = SubscriptionService(
        repo=mock_repo,
        payment_resolver=resolver,
        category_repo=category_repo,
    )
    create_dto = SubscriptionCreate(
        name="Spotify",
        category="servicos",
        amount=21.90,
        payment_method="nubank_joao",
    )

    created = await service.create(create_dto)
    assert created.credit_card_id is None
    assert created.account_id == account_id
    assert create_dto.account_id == account_id
    assert create_dto.payment_type == "DEBIT"


def make_subscription(subscription_id, **overrides) -> Subscription:
    fields = {
        "id": subscription_id,
        "name": "Netflix",
        "category": "servicos",
        "amount": 55.90,
        "payment_method": "itau_card_joao",
        "payment_type": "CREDIT",
    }
    fields.update(overrides)
    return Subscription(**fields)


async def test_update_subscription_rejects_unknown_category(mock_repo):
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = None
    service = SubscriptionService(
        repo=mock_repo,
        payment_resolver=FakePaymentResolver(),
        category_repo=category_repo,
    )

    with pytest.raises(ValidationError, match="não existe"):
        await service.update(uuid4(), SubscriptionUpdate(category="inexistente"))

    mock_repo.update.assert_not_awaited()


async def test_update_subscription_resolves_credit_card(mock_repo, category_repo):
    subscription_id = uuid4()
    card_id = uuid4()
    service = SubscriptionService(
        repo=mock_repo,
        payment_resolver=FakePaymentResolver(
            {
                "itau_card_joao": ResolvedPaymentTarget(
                    account_id=None, credit_card_id=card_id, payment_type="CREDIT"
                )
            }
        ),
        category_repo=category_repo,
    )
    subscription = make_subscription(subscription_id, credit_card_id=card_id)
    mock_repo.get_by_id.return_value = subscription
    mock_repo.update.return_value = subscription

    update_data = SubscriptionUpdate(payment_method="itau_card_joao")
    result = await service.update(subscription_id, update_data)

    assert update_data.credit_card_id == card_id
    assert update_data.payment_type == "CREDIT"
    assert result is subscription


async def test_update_subscription_raises_when_missing(mock_repo, category_repo, payment_resolver):
    mock_repo.get_by_id.return_value = None
    service = SubscriptionService(
        repo=mock_repo,
        payment_resolver=payment_resolver,
        category_repo=category_repo,
    )

    with pytest.raises(EntityNotFoundError, match="não encontrada"):
        await service.update(uuid4(), SubscriptionUpdate(amount=10.0))

    mock_repo.update.assert_not_awaited()


async def test_update_subscription_raises_when_repository_returns_none(
    mock_repo, category_repo, payment_resolver
):
    subscription_id = uuid4()
    mock_repo.get_by_id.return_value = make_subscription(subscription_id)
    mock_repo.update.return_value = None
    service = SubscriptionService(
        repo=mock_repo,
        payment_resolver=payment_resolver,
        category_repo=category_repo,
    )

    with pytest.raises(EntityNotFoundError, match="não encontrada"):
        await service.update(subscription_id, SubscriptionUpdate(amount=10.0))
