from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.models.credit_cards import CreditCard
from finance_api.repositories.credit_cards import CreditCardRepository
from finance_api.schemas.credit_cards import CreditCardCreate, CreditCardUpdate

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    return AsyncMock()


async def test_create_credit_card(mock_db):
    repo = CreditCardRepository(mock_db)
    account_id = uuid4()
    data = CreditCardCreate(
        key="itau_card_joao",
        name="Itaú Black",
        account_id=account_id,
        closing_day=2,
        due_day=10,
        credit_limit=15000.0,
    )
    result = await repo.create(data)

    assert result.key == "itau_card_joao"
    assert result.closing_day == 2
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


async def test_get_by_id(mock_db):
    card_id = uuid4()
    mock_card = CreditCard(id=card_id, key="itau_card_joao", name="Itaú Black")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_card
    mock_db.execute.return_value = mock_result

    repo = CreditCardRepository(mock_db)
    result = await repo.get_by_id(card_id)

    assert result == mock_card


async def test_list_credit_cards(mock_db):
    mock_card = CreditCard(id=uuid4(), key="itau_card_joao", name="Itaú Black")

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [mock_card]

    res1 = MagicMock()
    res1.scalars.return_value = scalars_mock

    res2 = MagicMock()
    scalars_count = MagicMock()
    scalars_count.all.return_value = [mock_card]
    res2.scalars.return_value = scalars_count

    mock_db.execute.side_effect = [res1, res2]

    repo = CreditCardRepository(mock_db)
    items, total = await repo.list(page=1, size=10)

    assert len(items) == 1
    assert total == 1


async def test_update_credit_card(mock_db):
    card_id = uuid4()
    mock_card = CreditCard(id=card_id, key="itau_card_joao", name="Itaú Black")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_card
    mock_db.execute.return_value = mock_result

    repo = CreditCardRepository(mock_db)
    updated = await repo.update(card_id, CreditCardUpdate(credit_limit=20000.0))

    assert updated.credit_limit == 20000.0
    mock_db.commit.assert_awaited_once()


async def test_delete_credit_card(mock_db):
    card_id = uuid4()
    mock_card = CreditCard(id=card_id, key="itau_card_joao", name="Itaú Black")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_card
    mock_db.execute.return_value = mock_result

    repo = CreditCardRepository(mock_db)
    success = await repo.delete(card_id)

    assert success is True
    mock_db.delete.assert_awaited_once_with(mock_card)
