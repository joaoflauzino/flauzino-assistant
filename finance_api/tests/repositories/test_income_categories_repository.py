from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.repositories.income_categories import IncomeCategoryRepository
from finance_api.schemas.income_categories import IncomeCategoryCreate, IncomeCategoryUpdate


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = 0
    mock_result.rowcount = 1
    session.execute.return_value = mock_result
    return session


@pytest.mark.asyncio
async def test_create_income_category(mock_db_session):
    repo = IncomeCategoryRepository(mock_db_session)
    category_data = IncomeCategoryCreate(key="salario", display_name="Salário")

    category = await repo.create(category_data)

    assert category.key == "salario"
    assert category.display_name == "Salário"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_income_categories(mock_db_session):
    repo = IncomeCategoryRepository(mock_db_session)

    mock_count = MagicMock()
    mock_count.scalar.return_value = 2

    mock_items = MagicMock()
    c1 = MagicMock()
    c1.key = "salario"
    c2 = MagicMock()
    c2.key = "pix"
    mock_items.scalars.return_value.all.return_value = [c1, c2]

    mock_db_session.execute.side_effect = [mock_count, mock_items]

    items, total = await repo.list()

    assert total == 2
    assert len(items) == 2
    assert items[0].key == "salario"


@pytest.mark.asyncio
async def test_get_by_key(mock_db_session):
    repo = IncomeCategoryRepository(mock_db_session)

    mock_result = MagicMock()
    mock_cat = MagicMock()
    mock_cat.key = "investimentos"
    mock_result.scalar_one_or_none.return_value = mock_cat

    mock_db_session.execute.return_value = mock_result

    found = await repo.get_by_key("investimentos")
    assert found is not None
    assert found.key == "investimentos"


@pytest.mark.asyncio
async def test_get_by_key_normalized(mock_db_session):
    repo = IncomeCategoryRepository(mock_db_session)

    mock_result_exact = MagicMock()
    mock_result_exact.scalar_one_or_none.return_value = None

    mock_result_all = MagicMock()
    mock_cat = MagicMock()
    mock_cat.key = "premiacao"
    mock_cat.display_name = "Premiação"
    mock_result_all.scalars.return_value.all.return_value = [mock_cat]

    mock_db_session.execute.side_effect = [mock_result_exact, mock_result_all]

    found = await repo.get_by_key("premiacao")
    assert found is not None
    assert found.key == "premiacao"


@pytest.mark.asyncio
async def test_get_by_id(mock_db_session):
    repo = IncomeCategoryRepository(mock_db_session)

    mock_result = MagicMock()
    mock_cat = MagicMock()
    mock_cat.key = "salario"
    mock_result.scalar_one_or_none.return_value = mock_cat
    mock_db_session.execute.return_value = mock_result

    cat_id = uuid4()
    found = await repo.get_by_id(cat_id)
    assert found is not None
    assert found.key == "salario"


@pytest.mark.asyncio
async def test_update_income_category(mock_db_session):
    repo = IncomeCategoryRepository(mock_db_session)

    mock_result = MagicMock()
    mock_cat = MagicMock()
    mock_cat.display_name = "Salário Empresa"
    mock_cat.key = "salario"
    mock_result.scalar_one_or_none.return_value = mock_cat
    mock_db_session.execute.return_value = mock_result

    cat_id = uuid4()
    updated = await repo.update(cat_id, IncomeCategoryUpdate(display_name="Salário Empresa"))
    assert updated is not None
    assert updated.display_name == "Salário Empresa"


@pytest.mark.asyncio
async def test_delete_income_category(mock_db_session):
    repo = IncomeCategoryRepository(mock_db_session)

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db_session.execute.return_value = mock_result

    cat_id = uuid4()
    success = await repo.delete(cat_id)
    assert success is True
