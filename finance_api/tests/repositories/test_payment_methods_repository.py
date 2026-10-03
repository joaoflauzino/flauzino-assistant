from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.models.credit_cards import CreditCard
from finance_api.models.accounts import Account
from finance_api.models.payment_methods import PaymentMethod
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.schemas.payment_methods import PaymentMethodCreate


@pytest.fixture
def mock_db_session():
    """Fixture for a mocked async database session."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    session.add = MagicMock()
    return session


async def test_create_payment_method_with_credit_card_fields(mock_db_session):
    repo = PaymentMethodRepository(mock_db_session)
    data = PaymentMethodCreate(
        key="c6_joao",
        display_name="C6 João",
        is_credit_card=True,
        closing_day=28,
        due_day=5,
    )

    await repo.create(data)

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()

    added = mock_db_session.add.call_args[0][0]
    assert added.key == "c6_joao"
    assert added.display_name == "C6 João"
    assert added.is_credit_card is True
    assert added.closing_day == 28
    assert added.due_day == 5


async def test_empty_string_converted_to_none_in_schema():
    data = PaymentMethodCreate(
        key="c6_joao",
        display_name="C6 João",
        is_credit_card=True,
        closing_day="",  # type: ignore
        due_day="",  # type: ignore
    )
    assert data.closing_day is None
    assert data.due_day is None


async def test_list_credit_cards(mock_db_session):
    repo = PaymentMethodRepository(mock_db_session)
    card1 = PaymentMethod(key="c6", display_name="C6", is_credit_card=True)
    card2 = PaymentMethod(key="nubank", display_name="Nubank", is_credit_card=True)

    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [card1, card2]

    results = await repo.list_credit_cards()

    assert len(results) == 2
    assert results[0].key == "c6"
    assert results[1].key == "nubank"


async def test_get_by_key_falls_back_to_credit_card():
    mock_session = AsyncMock()
    # 1st execute for PaymentMethod table (returns None), 2nd for CreditCard table (returns card)
    fake_card = CreditCard(
        id=uuid4(),
        key="c6_card_joao",
        name="C6 Carbon Black",
        account_id=uuid4(),
        closing_day=2,
        due_day=10,
        credit_limit=12000.0,
    )
    res_pm = MagicMock()
    res_pm.scalar_one_or_none.return_value = None
    res_card = MagicMock()
    res_card.scalar_one_or_none.return_value = fake_card

    mock_session.execute.side_effect = [res_pm, res_card]

    repo = PaymentMethodRepository(mock_session)
    result = await repo.get_by_key("c6_card_joao")

    assert result is not None
    assert result.key == "c6_card_joao"
    assert result.display_name == "C6 Carbon Black"
    assert result.is_credit_card is True
    assert result.closing_day == 2
    assert result.due_day == 10


async def test_get_by_key_falls_back_to_account():
    mock_session = AsyncMock()
    # 1st execute for PaymentMethod table (None), 2nd for CreditCard (None), 3rd for Account
    fake_account = Account(
        id=uuid4(),
        key="c6_joao",
        name="C6 João",
        bank="c6",
        owner="joao",
        type="CHECKING",
    )
    res_pm = MagicMock()
    res_pm.scalar_one_or_none.return_value = None
    res_card = MagicMock()
    res_card.scalar_one_or_none.return_value = None
    res_acc = MagicMock()
    res_acc.scalar_one_or_none.return_value = fake_account

    mock_session.execute.side_effect = [res_pm, res_card, res_acc]

    repo = PaymentMethodRepository(mock_session)
    result = await repo.get_by_key("c6_joao")

    assert result is not None
    assert result.key == "c6_joao"
    assert result.display_name == "C6 João"
    assert result.is_credit_card is False
