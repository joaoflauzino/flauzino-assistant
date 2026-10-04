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
from finance_api.models.incomes import Income
from finance_api.models.payment_methods import PaymentMethod
from finance_api.models.spents import Spent

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_client():
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


@pytest.fixture
def mock_income_repo(mocker):
    repo = MagicMock()
    repo.db = AsyncMock()
    repo.create = AsyncMock()
    repo.list = AsyncMock()
    repo.list_by_period = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()

    mocker.patch("finance_api.core.dependencies.IncomeRepository", return_value=repo)
    return repo


@pytest.fixture
def mock_income_cat_repo(mocker):
    repo = MagicMock()
    repo.db = AsyncMock()
    repo.get_by_key = AsyncMock()
    mocker.patch(
        "finance_api.core.dependencies.IncomeCategoryRepository",
        return_value=repo,
    )
    return repo


@pytest.fixture
def mock_pm_repo(mocker):
    repo = MagicMock()
    repo.db = AsyncMock()
    repo.get_by_key = AsyncMock()
    mocker.patch(
        "finance_api.core.dependencies.PaymentMethodRepository",
        return_value=repo,
    )
    return repo


@pytest.fixture
def mock_spent_repo(mocker):
    repo = MagicMock()
    repo.db = AsyncMock()
    repo.list = AsyncMock()
    mocker.patch("finance_api.core.dependencies.SpentRepository", return_value=repo)
    return repo


async def test_create_income_api(test_client, mock_income_repo, mock_income_cat_repo, mock_pm_repo):
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db

    mock_income_cat_repo.get_by_key.return_value = IncomeCategory(
        id=uuid4(), key="salario", display_name="Salário"
    )
    mock_pm_repo.get_by_key.return_value = PaymentMethod(
        id=uuid4(), key="itau_joao", display_name="Itaú"
    )

    inc = Income(
        id=uuid4(),
        description="Salário João",
        amount=7000.0,
        category="salario",
        payment_method="itau_joao",
        received_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    mock_income_repo.create.return_value = inc

    payload = {
        "description": "Salário João",
        "amount": 7000.0,
        "category": "salario",
        "payment_method": "itau_joao",
    }
    response = await test_client.post("/incomes/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["description"] == "Salário João"
    assert data["amount"] == 7000.0

    app.dependency_overrides.clear()


async def test_list_incomes_api(test_client, mock_income_repo):
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db

    inc = Income(
        id=uuid4(),
        description="Pix Recebido",
        amount=350.0,
        category="pix",
        received_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    mock_income_repo.list.return_value = ([inc], 1)

    response = await test_client.get("/incomes/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "pix"

    app.dependency_overrides.clear()


async def test_get_monthly_summary_api(test_client, mock_income_repo, mock_spent_repo):
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db

    inc = Income(
        id=uuid4(),
        description="Salário",
        amount=10000.0,
        category="salario",
        received_at=datetime(2026, 8, 5, tzinfo=ZoneInfo("America/Sao_Paulo")),
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    mock_income_repo.list_by_period.return_value = [inc]

    sp = Spent(
        id=uuid4(),
        item_bought="Aluguel",
        amount=3000.0,
        category="moradia",
        payment_method="itau_joao",
        location="Imobiliária",
        created_at=datetime(2026, 8, 10, tzinfo=ZoneInfo("America/Sao_Paulo")),
    )
    mock_spent_repo.list.return_value = ([sp], 1)

    response = await test_client.get("/incomes/summary?reference_month=2026-08")
    assert response.status_code == 200
    data = response.json()
    assert data["reference_month"] == "2026-08"
    assert data["total_incomes"] == 10000.0
    assert data["total_spents"] == 3000.0
    assert data["net_balance"] == 7000.0
    assert data["is_positive"] is True
    assert data["savings_rate"] == 70.0

    app.dependency_overrides.clear()


async def test_get_period_summary_api(test_client, mock_income_repo, mock_spent_repo):
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db

    inc = Income(
        id=uuid4(),
        description="Salário",
        amount=5000.0,
        category="salario",
        received_at=datetime(2026, 8, 5, tzinfo=ZoneInfo("America/Sao_Paulo")),
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    mock_income_repo.list_by_period.return_value = [inc]

    sp = Spent(
        id=uuid4(),
        item_bought="Aluguel",
        amount=2000.0,
        category="moradia",
        payment_method="itau_joao",
        location="Imobiliária",
        created_at=datetime(2026, 8, 10, tzinfo=ZoneInfo("America/Sao_Paulo")),
    )
    mock_spent_repo.list.return_value = ([sp], 1)

    response = await test_client.get("/incomes/summary?start_date=2026-01-01&end_date=2026-10-04")
    assert response.status_code == 200
    data = response.json()
    assert data["reference_month"] == "2026-01-01 a 2026-10-04"
    assert data["total_incomes"] == 5000.0
    assert data["total_spents"] == 2000.0
    assert data["net_balance"] == 3000.0

    app.dependency_overrides.clear()
