from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.models.accounts import Account
from finance_api.repositories.accounts import AccountRepository
from finance_api.schemas.accounts import AccountCreate, AccountUpdate

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


async def test_create_account(mock_db):
    repo = AccountRepository(mock_db)
    data = AccountCreate(
        key="itau_joao",
        name="Itaú João",
        bank="itau",
        owner="joao",
        type="CHECKING",
    )
    result = await repo.create(data)

    assert result.key == "itau_joao"
    assert result.name == "Itaú João"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


async def test_get_by_id(mock_db):
    account_id = uuid4()
    mock_account = Account(id=account_id, key="itau_joao", name="Itaú João")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_account
    mock_db.execute.return_value = mock_result

    repo = AccountRepository(mock_db)
    result = await repo.get_by_id(account_id)

    assert result == mock_account
    mock_db.execute.assert_awaited_once()


async def test_get_by_key(mock_db):
    mock_account = Account(id=uuid4(), key="itau_joao", name="Itaú João")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_account
    mock_db.execute.return_value = mock_result

    repo = AccountRepository(mock_db)
    result = await repo.get_by_key("ITAU_JOAO")

    assert result == mock_account


async def test_list_accounts(mock_db):
    mock_account = Account(id=uuid4(), key="itau_joao", name="Itaú João")

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [mock_account]

    res1 = MagicMock()
    res1.scalars.return_value = scalars_mock

    res2 = MagicMock()
    scalars_count = MagicMock()
    scalars_count.all.return_value = [mock_account]
    res2.scalars.return_value = scalars_count

    mock_db.execute.side_effect = [res1, res2]

    repo = AccountRepository(mock_db)
    items, total = await repo.list(page=1, size=10, owner="joao")

    assert len(items) == 1
    assert total == 1


async def test_update_account(mock_db):
    account_id = uuid4()
    mock_account = Account(id=account_id, key="itau_joao", name="Itaú João")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_account
    mock_db.execute.return_value = mock_result

    repo = AccountRepository(mock_db)
    updated = await repo.update(account_id, AccountUpdate(name="Itaú Super"))

    assert updated.name == "Itaú Super"
    mock_db.commit.assert_awaited_once()


async def test_delete_account(mock_db):
    account_id = uuid4()
    mock_account = Account(id=account_id, key="itau_joao", name="Itaú João")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_account
    mock_db.execute.return_value = mock_result

    repo = AccountRepository(mock_db)
    success = await repo.delete(account_id)

    assert success is True
    mock_db.delete.assert_awaited_once_with(mock_account)
