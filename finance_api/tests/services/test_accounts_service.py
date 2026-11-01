from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import EntityConflictError, EntityNotFoundError
from finance_api.models.accounts import Account
from finance_api.schemas.accounts import AccountCreate, AccountUpdate
from finance_api.services.accounts import AccountService
from finance_api.tests.fakes.fake_account_repository import InMemoryAccountRepository

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_repo(mocker):
    repo = MagicMock()
    repo.list = mocker.AsyncMock(return_value=([], 0))
    repo.get_by_id = mocker.AsyncMock(return_value=None)
    repo.get_by_key = mocker.AsyncMock(return_value=None)
    repo.create = mocker.AsyncMock()
    repo.update = mocker.AsyncMock()
    repo.delete = mocker.AsyncMock()
    return repo


async def test_create_account_success(mock_repo):
    service = AccountService(repository=mock_repo)
    data = AccountCreate(
        key="nubank_lailla",
        name="Nubank Lailla",
        bank="nubank",
        owner="lailla",
    )
    expected = Account(id=uuid4(), key="nubank_lailla", name="Nubank Lailla")
    mock_repo.create.return_value = expected

    result = await service.create(data)

    assert result == expected
    mock_repo.get_by_key.assert_awaited_once_with("nubank_lailla")
    mock_repo.create.assert_awaited_once_with(data)


async def test_create_account_conflict(mock_repo):
    service = AccountService(repository=mock_repo)
    data = AccountCreate(
        key="nubank_lailla",
        name="Nubank Lailla",
        bank="nubank",
        owner="lailla",
    )
    mock_repo.get_by_key.return_value = Account(id=uuid4(), key="nubank_lailla")

    with pytest.raises(EntityConflictError):
        await service.create(data)


async def test_get_by_id_not_found(mock_repo):
    service = AccountService(repository=mock_repo)
    fake_id = uuid4()

    with pytest.raises(EntityNotFoundError):
        await service.get_by_id(fake_id)


async def test_delete_account_not_found(mock_repo):
    service = AccountService(repository=mock_repo)
    fake_id = uuid4()
    mock_repo.delete.return_value = False

    with pytest.raises(EntityNotFoundError):
        await service.delete(fake_id)


async def test_account_service_with_in_memory_fake_repository() -> None:
    """Validates AccountService using InMemoryAccountRepository (Protocol structural subtyping)."""
    fake_repo = InMemoryAccountRepository()
    service = AccountService(repository=fake_repo)

    created = await service.create(
        AccountCreate(key="c6_joao", name="C6 João", bank="c6", owner="joao")
    )
    assert created.key == "c6_joao"

    second = await service.create(
        AccountCreate(key="nubank_lailla", name="Nubank Lailla", bank="nubank", owner="lailla")
    )

    items, total = await service.list(page=1, size=10, owner="joao")
    assert total == 1
    assert items[0].id == created.id

    by_key = await service.get_by_key("C6_JOAO")
    assert by_key.id == created.id

    with pytest.raises(EntityNotFoundError):
        await service.get_by_key("inexistente")

    with pytest.raises(EntityConflictError):
        await service.create(
            AccountCreate(key="c6_joao", name="Duplicada", bank="c6", owner="joao")
        )

    # Conflict on update key to another existing account's key
    with pytest.raises(EntityConflictError):
        await service.update(created.id, AccountUpdate(key=second.key))

    updated = await service.update(created.id, AccountUpdate(key="C6_CARBON", name="C6 Carbon"))
    assert updated.name == "C6 Carbon"
    assert updated.key == "c6_carbon"

    with pytest.raises(EntityNotFoundError):
        await service.update(uuid4(), AccountUpdate(name="Ghost"))

    await service.delete(created.id)
    with pytest.raises(EntityNotFoundError):
        await service.get_by_id(created.id)
