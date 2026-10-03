from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import EntityConflictError, EntityNotFoundError
from finance_api.models.accounts import Account
from finance_api.models.credit_cards import CreditCard
from finance_api.schemas.credit_cards import CreditCardCreate
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
