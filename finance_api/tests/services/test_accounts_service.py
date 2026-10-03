from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import EntityConflictError, EntityNotFoundError
from finance_api.models.accounts import Account
from finance_api.schemas.accounts import AccountCreate
from finance_api.services.accounts import AccountService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    return repo


async def test_list_accounts(mock_repo):
    service = AccountService(mock_repo)
    mock_repo.list.return_value = ([], 0)

    items, total = await service.list(page=1, size=10, owner="joao")
    assert items == []
    assert total == 0
    mock_repo.list.assert_awaited_once_with(1, 10, "joao")


async def test_get_by_id_found(mock_repo):
    service = AccountService(mock_repo)
    fake_id = uuid4()
    mock_account = Account(id=fake_id, key="itau_joao", name="Itaú João")
    mock_repo.get_by_id.return_value = mock_account

    result = await service.get_by_id(fake_id)
    assert result == mock_account


async def test_get_by_id_not_found(mock_repo):
    service = AccountService(mock_repo)
    fake_id = uuid4()
    mock_repo.get_by_id.return_value = None

    with pytest.raises(EntityNotFoundError):
        await service.get_by_id(fake_id)


async def test_create_account_success(mock_repo):
    service = AccountService(mock_repo)
    data = AccountCreate(key="nubank_joao", name="Nubank", bank="nubank", owner="joao")
    mock_repo.get_by_key.return_value = None
    mock_account = Account(id=uuid4(), key="nubank_joao", name="Nubank")
    mock_repo.create.return_value = mock_account

    result = await service.create(data)
    assert result == mock_account


async def test_create_account_conflict(mock_repo):
    service = AccountService(mock_repo)
    data = AccountCreate(key="nubank_joao", name="Nubank", bank="nubank", owner="joao")
    mock_repo.get_by_key.return_value = Account(id=uuid4(), key="nubank_joao")

    with pytest.raises(EntityConflictError):
        await service.create(data)


async def test_delete_account_not_found(mock_repo):
    service = AccountService(mock_repo)
    fake_id = uuid4()
    mock_repo.delete.return_value = False

    with pytest.raises(EntityNotFoundError):
        await service.delete(fake_id)
