from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.schemas.limits import SpendingLimitCreate
from finance_api.services.limits import SpendingLimitService


@pytest.mark.asyncio
async def test_create_spending_limit_with_valid_injected_category_repo():
    mock_limit_repo = MagicMock(spec=SpendingLimitRepository)
    mock_limit_repo.create = AsyncMock(
        return_value=MagicMock(id=uuid4(), category="mercado", amount=1500.0)
    )

    mock_category_repo = MagicMock(spec=CategoryRepository)
    mock_category_repo.get_by_key = AsyncMock(return_value=MagicMock(key="mercado"))

    service = SpendingLimitService(repo=mock_limit_repo, category_repo=mock_category_repo)

    result = await service.create(SpendingLimitCreate(category="mercado", amount=1500.0))

    assert result.category == "mercado"
    mock_category_repo.get_by_key.assert_awaited_once_with("mercado")
    mock_limit_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_spending_limit_fails_when_category_not_found():
    mock_limit_repo = MagicMock(spec=SpendingLimitRepository)
    mock_category_repo = MagicMock(spec=CategoryRepository)
    mock_category_repo.get_by_key = AsyncMock(return_value=None)

    service = SpendingLimitService(repo=mock_limit_repo, category_repo=mock_category_repo)

    with pytest.raises(ValidationError, match="Categoria 'inexistente' não existe"):
        await service.create(SpendingLimitCreate(category="inexistente", amount=500.0))

    mock_category_repo.get_by_key.assert_awaited_once_with("inexistente")
    mock_limit_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_spending_limit_get_by_id_not_found():
    mock_limit_repo = MagicMock(spec=SpendingLimitRepository)
    mock_limit_repo.get_by_id = AsyncMock(return_value=None)
    mock_category_repo = MagicMock(spec=CategoryRepository)

    service = SpendingLimitService(repo=mock_limit_repo, category_repo=mock_category_repo)
    non_existent_id = uuid4()

    with pytest.raises(EntityNotFoundError):
        await service.get_by_id(non_existent_id)


@pytest.mark.asyncio
async def test_spending_limit_delete_not_found():
    mock_limit_repo = MagicMock(spec=SpendingLimitRepository)
    mock_limit_repo.delete = AsyncMock(return_value=False)
    mock_category_repo = MagicMock(spec=CategoryRepository)

    service = SpendingLimitService(repo=mock_limit_repo, category_repo=mock_category_repo)

    with pytest.raises(EntityNotFoundError):
        await service.delete(uuid4())
