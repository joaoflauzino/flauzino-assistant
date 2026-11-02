from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import EntityConflictError, EntityNotFoundError
from finance_api.models.accounts import Account
from finance_api.models.credit_cards import CreditCard
from finance_api.schemas.credit_cards import CreditCardCreate, CreditCardUpdate
from finance_api.services.credit_cards import CreditCardService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_card_repo():
    return AsyncMock()


@pytest.fixture
def mock_account_repo():
    return AsyncMock()


async def test_create_credit_card_success(mock_card_repo, mock_account_repo):
    service = CreditCardService(mock_card_repo, mock_account_repo)
    acc_id = uuid4()
    mock_account_repo.get_by_id.return_value = Account(id=acc_id, key="itau_joao")
    mock_card_repo.get_by_key.return_value = None

    data = CreditCardCreate(
        key="itau_black",
        name="Itaú Black",
        account_id=acc_id,
        closing_day=2,
        due_day=10,
        credit_limit=10000.0,
    )
    mock_card = CreditCard(id=uuid4(), key="itau_black")
    mock_card_repo.create.return_value = mock_card

    result = await service.create(data)
    assert result == mock_card


async def test_create_credit_card_account_not_found(mock_card_repo, mock_account_repo):
    service = CreditCardService(mock_card_repo, mock_account_repo)
    acc_id = uuid4()
    mock_account_repo.get_by_id.return_value = None

    data = CreditCardCreate(
        key="itau_black",
        name="Itaú Black",
        account_id=acc_id,
        closing_day=2,
        due_day=10,
    )

    with pytest.raises(EntityNotFoundError):
        await service.create(data)


async def test_create_credit_card_conflict(mock_card_repo, mock_account_repo):
    service = CreditCardService(mock_card_repo, mock_account_repo)
    acc_id = uuid4()
    mock_account_repo.get_by_id.return_value = Account(id=acc_id, key="itau_joao")
    mock_card_repo.get_by_key.return_value = CreditCard(id=uuid4(), key="itau_black")

    data = CreditCardCreate(
        key="itau_black",
        name="Itaú Black",
        account_id=acc_id,
        closing_day=2,
        due_day=10,
    )

    with pytest.raises(EntityConflictError):
        await service.create(data)


async def test_update_credit_card_success(mock_card_repo):
    card_id = uuid4()
    service = CreditCardService(mock_card_repo)
    updated_card = CreditCard(id=card_id, key="itau_black", name="Itaú Black")
    mock_card_repo.update.return_value = updated_card

    result = await service.update(card_id, CreditCardUpdate(name="Itaú Black"))

    assert result is updated_card
    mock_card_repo.update.assert_awaited_once()


async def test_update_credit_card_account_not_found(mock_card_repo, mock_account_repo):
    service = CreditCardService(mock_card_repo, mock_account_repo)
    mock_account_repo.get_by_id.return_value = None

    with pytest.raises(EntityNotFoundError, match="Conta vinculada"):
        await service.update(uuid4(), CreditCardUpdate(account_id=uuid4()))

    mock_card_repo.update.assert_not_awaited()


async def test_update_credit_card_key_conflict_with_other_card(mock_card_repo):
    card_id = uuid4()
    service = CreditCardService(mock_card_repo)
    mock_card_repo.get_by_key.return_value = CreditCard(
        id=uuid4(), key="itau_black", name="Outro cartão"
    )

    with pytest.raises(EntityConflictError, match="já existe"):
        await service.update(card_id, CreditCardUpdate(key="itau_black"))

    mock_card_repo.update.assert_not_awaited()


async def test_update_credit_card_keeps_own_key(mock_card_repo):
    card_id = uuid4()
    service = CreditCardService(mock_card_repo)
    mock_card_repo.get_by_key.return_value = CreditCard(
        id=card_id, key="itau_black", name="Itaú Black"
    )
    updated_card = CreditCard(id=card_id, key="itau_black", name="Itaú Black")
    mock_card_repo.update.return_value = updated_card

    result = await service.update(card_id, CreditCardUpdate(key="itau_black"))

    assert result is updated_card


async def test_update_credit_card_raises_when_repository_returns_none(mock_card_repo):
    mock_card_repo.update.return_value = None
    service = CreditCardService(mock_card_repo)

    with pytest.raises(EntityNotFoundError, match="não encontrado"):
        await service.update(uuid4(), CreditCardUpdate(name="Itaú Black"))
