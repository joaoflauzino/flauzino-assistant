from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from finance_api.models.accounts import Account
from finance_api.models.credit_cards import CreditCard
from finance_api.models.payment_methods import PaymentMethod
from finance_api.repositories.payment_methods import (
    PaymentMethodRepository,
    payment_method_from_account,
    payment_method_from_credit_card,
)
from finance_api.schemas.payment_methods import PaymentMethodCreate


def make_credit_card(key: str, name: str, **overrides) -> CreditCard:
    fields = {
        "id": uuid4(),
        "key": key,
        "name": name,
        "account_id": uuid4(),
        "closing_day": 2,
        "due_day": 10,
        "credit_limit": 12000.0,
    }
    fields.update(overrides)
    return CreditCard(**fields)


def make_account(key: str, name: str, bank: str = "c6", **overrides) -> Account:
    fields = {
        "id": uuid4(),
        "key": key,
        "name": name,
        "bank": bank,
        "owner": "joao",
        "type": "CHECKING",
    }
    fields.update(overrides)
    return Account(**fields)


def make_result(items: list) -> MagicMock:
    """Builds a fake execute() result whose scalars().all() returns ``items``."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.scalar_one_or_none.return_value = None
    return result


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
    card1 = make_credit_card("c6", "C6")
    card2 = make_credit_card("nubank", "Nubank")

    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [card1, card2]

    results = await repo.list_credit_cards()

    assert len(results) == 2
    assert results[0].key == "c6"
    assert results[0].display_name == "C6"
    assert results[0].is_credit_card is True
    assert results[0].closing_day == 2
    assert results[0].due_day == 10
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


async def test_get_by_key_finds_payment_method_table_first():
    mock_session = AsyncMock()
    method = PaymentMethod(key="pix_joao", display_name="Pix João", is_credit_card=False)
    res_pm = MagicMock()
    res_pm.scalar_one_or_none.return_value = method
    mock_session.execute.return_value = res_pm

    repo = PaymentMethodRepository(mock_session)
    result = await repo.get_by_key("pix_joao")

    assert result is method
    mock_session.execute.assert_awaited_once()


async def test_get_by_key_returns_none_when_not_found_anywhere():
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = res

    repo = PaymentMethodRepository(mock_session)
    result = await repo.get_by_key("metodo_fantasma")

    assert result is None
    assert mock_session.execute.await_count == 3


async def test_get_by_key_propagates_database_errors():
    """Database failures must surface instead of being swallowed into a silent None."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = SQLAlchemyError("connection lost")

    repo = PaymentMethodRepository(mock_session)

    with pytest.raises(SQLAlchemyError):
        await repo.get_by_key("pix_joao")


async def test_list_derives_cards_and_accounts_before_stored_methods():
    mock_session = AsyncMock()
    card = make_credit_card("c6_card", "C6 Carbon")
    account = make_account("c6_joao", "C6 João", bank="c6")
    mock_session.execute.side_effect = [make_result([card]), make_result([account])]

    repo = PaymentMethodRepository(mock_session)
    items, total = await repo.list()

    assert total == 2
    assert [item.key for item in items] == ["c6_card", "c6_joao"]
    assert items[0].is_credit_card is True
    assert items[0].display_name == "C6 Carbon"
    assert items[1].is_credit_card is False
    assert items[1].display_name == "C6 João (c6)"
    assert mock_session.execute.await_count == 2


async def test_list_paginates_derived_items():
    mock_session = AsyncMock()
    first = make_credit_card("c6_card", "C6 Carbon")
    second = make_credit_card("nubank_card", "Nubank Ultravioleta")
    mock_session.execute.side_effect = [make_result([first, second]), make_result([])]

    repo = PaymentMethodRepository(mock_session)
    items, total = await repo.list(page=2, size=1)

    assert total == 2
    assert [item.key for item in items] == ["nubank_card"]


async def test_list_falls_back_to_stored_payment_methods():
    mock_session = AsyncMock()
    stored = PaymentMethod(key="pix_joao", display_name="Pix João", is_credit_card=False)
    mock_session.execute.side_effect = [
        make_result([]),
        make_result([]),
        make_result([stored]),
        make_result([stored]),
    ]

    repo = PaymentMethodRepository(mock_session)
    items, total = await repo.list()

    assert [item.key for item in items] == ["pix_joao"]
    assert total == 1


async def test_list_credit_cards_falls_back_to_stored_when_card_table_is_empty():
    mock_session = AsyncMock()
    stored_card = PaymentMethod(key="c6", display_name="C6", is_credit_card=True)
    mock_session.execute.side_effect = [make_result([]), make_result([stored_card])]

    repo = PaymentMethodRepository(mock_session)
    results = await repo.list_credit_cards()

    assert [card.key for card in results] == ["c6"]


def test_payment_method_from_credit_card_maps_all_fields():
    card = make_credit_card("c6_card", "C6 Carbon", closing_day=3, due_day=11)

    method = payment_method_from_credit_card(card)

    assert method.id == card.id
    assert method.key == "c6_card"
    assert method.display_name == "C6 Carbon"
    assert method.is_credit_card is True
    assert method.closing_day == 3
    assert method.due_day == 11


def test_payment_method_from_account_omits_bank_by_default():
    account = make_account("c6_joao", "C6 João", bank="c6")

    method = payment_method_from_account(account)

    assert method.id == account.id
    assert method.key == "c6_joao"
    assert method.display_name == "C6 João"
    assert method.is_credit_card is False


def test_payment_method_from_account_includes_bank_when_requested():
    method = payment_method_from_account(
        make_account("c6_joao", "C6 João", bank="c6"), include_bank=True
    )

    assert method.display_name == "C6 João (c6)"


def test_payment_method_from_account_skips_empty_bank():
    method = payment_method_from_account(
        make_account("c6_joao", "C6 João", bank=""), include_bank=True
    )

    assert method.display_name == "C6 João"
