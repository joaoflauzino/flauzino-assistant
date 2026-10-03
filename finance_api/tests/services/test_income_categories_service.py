from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.models.income_categories import IncomeCategory
from finance_api.schemas.income_categories import IncomeCategoryCreate
from finance_api.services.income_categories import IncomeCategoryService


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.mark.asyncio
async def test_create_income_category_success(mock_repo):
    mock_repo.get_by_key.return_value = None
    created_model = IncomeCategory(
        id=uuid4(),
        key="salario",
        display_name="Salário",
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    mock_repo.create.return_value = created_model

    service = IncomeCategoryService(mock_repo)
    result = await service.create(IncomeCategoryCreate(key="salario", display_name="Salário"))

    assert result.key == "salario"
    assert result.display_name == "Salário"
    mock_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_income_category_conflict(mock_repo):
    mock_repo.get_by_key.return_value = MagicMock()

    service = IncomeCategoryService(mock_repo)
    with pytest.raises(ValidationError, match="já existe"):
        await service.create(IncomeCategoryCreate(key="salario", display_name="Salário"))


@pytest.mark.asyncio
async def test_list_income_categories(mock_repo):
    item = IncomeCategory(
        id=uuid4(),
        key="pix",
        display_name="Pix",
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    mock_repo.list.return_value = ([item], 1)

    service = IncomeCategoryService(mock_repo)
    items, total = await service.list(page=1, size=10)

    assert total == 1
    assert len(items) == 1
    assert items[0].key == "pix"


@pytest.mark.asyncio
async def test_get_by_id_not_found(mock_repo):
    mock_repo.get_by_id.return_value = None

    service = IncomeCategoryService(mock_repo)
    with pytest.raises(EntityNotFoundError):
        await service.get_by_id(uuid4())


@pytest.mark.asyncio
async def test_delete_not_found(mock_repo):
    mock_repo.delete.return_value = False

    service = IncomeCategoryService(mock_repo)
    with pytest.raises(EntityNotFoundError):
        await service.delete(uuid4())
