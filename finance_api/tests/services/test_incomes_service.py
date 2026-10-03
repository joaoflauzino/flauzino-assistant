from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.models.income_categories import IncomeCategory
from finance_api.models.incomes import Income
from finance_api.models.payment_methods import PaymentMethod
from finance_api.models.spents import Spent
from finance_api.schemas.incomes import IncomeCreate
from finance_api.services.incomes import IncomeService


@pytest.fixture
def mock_income_repo():
    return AsyncMock()


@pytest.fixture
def mock_cat_repo():
    return AsyncMock()


@pytest.fixture
def mock_pm_repo():
    return AsyncMock()


@pytest.fixture
def mock_spent_repo():
    return AsyncMock()


@pytest.fixture
def income_service(mock_income_repo, mock_cat_repo, mock_pm_repo, mock_spent_repo):
    return IncomeService(
        repo=mock_income_repo,
        category_repo=mock_cat_repo,
        pm_repo=mock_pm_repo,
        spent_repo=mock_spent_repo,
    )


@pytest.mark.asyncio
async def test_create_income_success(income_service, mock_income_repo, mock_cat_repo, mock_pm_repo):
    mock_cat_repo.get_by_key.return_value = IncomeCategory(
        id=uuid4(), key="salario", display_name="Salário"
    )
    mock_pm_repo.get_by_key.return_value = PaymentMethod(
        id=uuid4(), key="itau_joao", display_name="Itaú"
    )

    created_model = Income(
        id=uuid4(),
        description="Salário Mensal",
        amount=6000.0,
        category="salario",
        payment_method="itau_joao",
        received_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    mock_income_repo.create.return_value = created_model

    dto = IncomeCreate(
        description="Salário Mensal",
        amount=6000.0,
        category="salario",
        payment_method="itau_joao",
    )
    result = await income_service.create(dto)

    assert result.description == "Salário Mensal"
    assert result.amount == 6000.0
    mock_income_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_income_invalid_category(income_service, mock_cat_repo):
    mock_cat_repo.get_by_key.return_value = None

    dto = IncomeCreate(
        description="Premiação",
        amount=1000.0,
        category="inexistente",
    )
    with pytest.raises(ValidationError, match="não existe"):
        await income_service.create(dto)


@pytest.mark.asyncio
async def test_create_income_invalid_payment_method(income_service, mock_cat_repo, mock_pm_repo):
    mock_cat_repo.get_by_key.return_value = IncomeCategory(
        id=uuid4(), key="salario", display_name="Salário"
    )
    mock_pm_repo.get_by_key.return_value = None

    dto = IncomeCreate(
        description="Salário",
        amount=5000.0,
        category="salario",
        payment_method="cartao_fantasma",
    )
    with pytest.raises(ValidationError, match="Método de pagamento 'cartao_fantasma' não existe"):
        await income_service.create(dto)


@pytest.mark.asyncio
async def test_get_by_id_not_found(income_service, mock_income_repo):
    mock_income_repo.get_by_id.return_value = None

    with pytest.raises(EntityNotFoundError):
        await income_service.get_by_id(uuid4())


@pytest.mark.asyncio
async def test_monthly_summary_calculation(income_service, mock_income_repo, mock_spent_repo):
    inc1 = Income(
        id=uuid4(),
        description="Salário",
        amount=5000.0,
        category="salario",
        received_at=datetime(2026, 8, 5, tzinfo=ZoneInfo("America/Sao_Paulo")),
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    inc2 = Income(
        id=uuid4(),
        description="Pix",
        amount=1000.0,
        category="pix",
        received_at=datetime(2026, 8, 10, tzinfo=ZoneInfo("America/Sao_Paulo")),
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    mock_income_repo.list_by_period.return_value = [inc1, inc2]

    sp1 = Spent(
        id=uuid4(),
        item_bought="Mercado",
        amount=2000.0,
        category="mercado",
        payment_method="itau_joao",
        location="Super",
        created_at=datetime(2026, 8, 6, tzinfo=ZoneInfo("America/Sao_Paulo")),
    )
    sp2 = Spent(
        id=uuid4(),
        item_bought="Internet",
        amount=1000.0,
        category="servicos",
        payment_method="pix_joao",
        location="Casa",
        created_at=datetime(2026, 8, 7, tzinfo=ZoneInfo("America/Sao_Paulo")),
    )
    mock_spent_repo.list.return_value = ([sp1, sp2], 2)

    summary = await income_service.get_monthly_summary("2026-08")

    assert summary.reference_month == "2026-08"
    assert summary.total_incomes == 6000.0
    assert summary.total_spents == 3000.0
    assert summary.net_balance == 3000.0
    assert summary.is_positive is True
    assert summary.savings_rate == 50.0
    assert summary.incomes_by_category == {"salario": 5000.0, "pix": 1000.0}
    assert summary.spents_by_category == {"mercado": 2000.0, "servicos": 1000.0}


@pytest.mark.asyncio
async def test_monthly_summary_invalid_month_format(income_service):
    with pytest.raises(ValidationError, match="Formato de mês inválido"):
        await income_service.get_monthly_summary("2026/08")
