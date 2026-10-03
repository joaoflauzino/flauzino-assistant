from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.repositories.incomes import IncomeRepository
from finance_api.schemas.incomes import IncomeCreate, IncomeUpdate


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
async def test_create_income(mock_db_session):
    repo = IncomeRepository(mock_db_session)
    income_data = IncomeCreate(
        description="Salário",
        amount=5000.0,
        category="salario",
        payment_method="itau_joao",
    )

    income = await repo.create(income_data)

    assert income.description == "Salário"
    assert income.amount == 5000.0
    assert income.category == "salario"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_incomes(mock_db_session):
    repo = IncomeRepository(mock_db_session)

    mock_count = MagicMock()
    mock_count.scalar.return_value = 1
    mock_items = MagicMock()
    inc = MagicMock()
    inc.description = "Freelance"
    mock_items.scalars.return_value.all.return_value = [inc]

    mock_db_session.execute.side_effect = [mock_count, mock_items]

    items, total = await repo.list(
        skip=0,
        limit=10,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
        category="pix",
    )

    assert total == 1
    assert len(items) == 1
    assert items[0].description == "Freelance"


@pytest.mark.asyncio
async def test_list_by_period(mock_db_session):
    repo = IncomeRepository(mock_db_session)

    mock_items = MagicMock()
    inc = MagicMock()
    inc.amount = 3000.0
    mock_items.scalars.return_value.all.return_value = [inc]
    mock_db_session.execute.return_value = mock_items

    items = await repo.list_by_period(date(2026, 8, 1), date(2026, 8, 31))

    assert len(items) == 1
    assert items[0].amount == 3000.0


@pytest.mark.asyncio
async def test_get_by_id(mock_db_session):
    repo = IncomeRepository(mock_db_session)

    mock_result = MagicMock()
    inc = MagicMock()
    inc.description = "Bônus"
    mock_result.scalar_one_or_none.return_value = inc
    mock_db_session.execute.return_value = mock_result

    found = await repo.get_by_id(uuid4())
    assert found is not None
    assert found.description == "Bônus"


@pytest.mark.asyncio
async def test_update_income(mock_db_session):
    repo = IncomeRepository(mock_db_session)

    mock_result = MagicMock()
    inc = MagicMock()
    inc.amount = 6000.0
    mock_result.scalar_one_or_none.return_value = inc
    mock_db_session.execute.return_value = mock_result

    updated = await repo.update(uuid4(), IncomeUpdate(amount=6000.0))
    assert updated is not None
    assert updated.amount == 6000.0


@pytest.mark.asyncio
async def test_delete_income(mock_db_session):
    repo = IncomeRepository(mock_db_session)

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db_session.execute.return_value = mock_result

    deleted = await repo.delete(uuid4())
    assert deleted is True
