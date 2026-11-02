from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.models.accounts import Account
from finance_api.models.credit_cards import CreditCard
from finance_api.models.subscriptions import Subscription
from finance_api.schemas.payment_resolution import ResolvedPaymentTarget
from finance_api.schemas.subscriptions import SubscriptionCreate, SubscriptionUpdate
from finance_api.services.subscriptions import SubscriptionService
from finance_api.tests.fakes.fake_payment_resolver import FakePaymentResolver

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.db = AsyncMock()
    return repo


async def test_create_subscription_with_credit_card(mock_repo):
    card_id = uuid4()
    account_id = uuid4()
    fake_card = CreditCard(
        id=card_id,
        key="itau_card_joao",
        name="Itaú Card",
        account_id=account_id,
        closing_day=2,
        due_day=10,
    )

    # 1st execute for category check (get_by_key returns Category)
    res_cat = MagicMock()
    res_cat.scalar_one_or_none.return_value = MagicMock(key="servicos")
    # 2nd execute for CreditCard check
    res_card = MagicMock()
    res_card.scalar_one_or_none.return_value = fake_card

    mock_repo.db.execute.side_effect = [res_cat, res_card]

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

    service = SubscriptionService(mock_repo)
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


async def test_create_subscription_with_account(mock_repo):
    account_id = uuid4()
    fake_acc = Account(
        id=account_id,
        key="nubank_joao",
        name="Nubank",
        bank="nubank",
        owner="joao",
        type="CHECKING",
    )

    res_cat = MagicMock()
    res_cat.scalar_one_or_none.return_value = MagicMock(key="servicos")
    # CreditCard returns None, Account returns fake_acc
    res_card = MagicMock()
    res_card.scalar_one_or_none.return_value = None
    res_acc = MagicMock()
    res_acc.scalar_one_or_none.return_value = fake_acc

    mock_repo.db.execute.side_effect = [res_cat, res_card, res_acc]

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

    service = SubscriptionService(mock_repo)
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


async def test_update_subscription_rejects_unknown_category(mock_repo, mocker):
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = None
    mocker.patch(
        "finance_api.services.subscriptions.CategoryRepository", return_value=category_repo
    )

    service = SubscriptionService(mock_repo)

    with pytest.raises(ValidationError, match="não existe"):
        await service.update(uuid4(), SubscriptionUpdate(category="inexistente"))

    mock_repo.update.assert_not_awaited()


async def test_update_subscription_resolves_credit_card(mock_repo):
    subscription_id = uuid4()
    card_id = uuid4()
    service = SubscriptionService(
        mock_repo,
        payment_resolver=FakePaymentResolver(
            {
                "itau_card_joao": ResolvedPaymentTarget(
                    account_id=None, credit_card_id=card_id, payment_type="CREDIT"
                )
            }
        ),
    )
    subscription = make_subscription(subscription_id, credit_card_id=card_id)
    mock_repo.get_by_id.return_value = subscription
    mock_repo.update.return_value = subscription

    update_data = SubscriptionUpdate(payment_method="itau_card_joao")
    result = await service.update(subscription_id, update_data)

    assert update_data.credit_card_id == card_id
    assert update_data.payment_type == "CREDIT"
    assert result is subscription


async def test_update_subscription_raises_when_missing(mock_repo):
    mock_repo.get_by_id.return_value = None
    service = SubscriptionService(mock_repo)

    with pytest.raises(EntityNotFoundError, match="não encontrada"):
        await service.update(uuid4(), SubscriptionUpdate(amount=10.0))

    mock_repo.update.assert_not_awaited()


async def test_update_subscription_raises_when_repository_returns_none(mock_repo):
    subscription_id = uuid4()
    mock_repo.get_by_id.return_value = make_subscription(subscription_id)
    mock_repo.update.return_value = None
    service = SubscriptionService(mock_repo)

    with pytest.raises(EntityNotFoundError, match="não encontrada"):
        await service.update(subscription_id, SubscriptionUpdate(amount=10.0))
