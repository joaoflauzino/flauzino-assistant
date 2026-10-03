from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from finance_api.core.database import get_db
from finance_api.main import app
from finance_api.models.income_categories import IncomeCategory

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_client():
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


@pytest.fixture
def mock_income_cat_repo(mocker):
    repo = MagicMock()
    repo.db = AsyncMock()
    repo.create = AsyncMock()
    repo.list = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_key = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()

    mocker.patch(
        "finance_api.core.dependencies.IncomeCategoryRepository",
        return_value=repo,
    )
    return repo


async def test_list_income_categories_api(test_client, mock_income_cat_repo):
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db

    cat = IncomeCategory(
        id=uuid4(),
        key="salario",
        display_name="Salário",
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    mock_income_cat_repo.list.return_value = ([cat], 1)

    response = await test_client.get("/income-categories/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["key"] == "salario"

    app.dependency_overrides.clear()


async def test_create_income_category_api(test_client, mock_income_cat_repo):
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db

    mock_income_cat_repo.get_by_key.return_value = None
    cat = IncomeCategory(
        id=uuid4(),
        key="investimentos",
        display_name="Investimentos",
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    mock_income_cat_repo.create.return_value = cat

    response = await test_client.post(
        "/income-categories/",
        json={"key": "investimentos", "display_name": "Investimentos"},
    )
    assert response.status_code == 201
    assert response.json()["key"] == "investimentos"

    app.dependency_overrides.clear()
