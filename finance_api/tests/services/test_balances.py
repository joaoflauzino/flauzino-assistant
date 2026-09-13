from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pytest

from finance_api.core.dependencies import get_balance_service
from finance_api.models.limits import SpendingLimit
from finance_api.models.payment_methods import PaymentMethod
from finance_api.models.spents import Spent
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.repositories.spents import SpentRepository
from finance_api.services.balances import BalanceService
from finance_api.services.invoices import InvoiceService


@pytest.fixture
def balance_service():
    return BalanceService(
        limit_repo=MagicMock(spec=SpendingLimitRepository),
        spent_repo=MagicMock(spec=SpentRepository),
        category_repo=MagicMock(spec=CategoryRepository),
        pm_repo=MagicMock(spec=PaymentMethodRepository),
        inv_service=MagicMock(spec=InvoiceService),
    )


def test_aggregate_spents_by_category(balance_service):
    spent1 = MagicMock(spec=Spent, category="mercado", amount=150.0)
    spent2 = MagicMock(spec=Spent, category="mercado", amount=50.0)
    spent3 = MagicMock(spec=Spent, category="transporte", amount=30.0)

    result = balance_service._aggregate_spents_by_category([spent1, spent2, spent3])

    assert result == {"mercado": 200.0, "transporte": 30.0}


def test_build_balances_with_and_without_limits(balance_service):
    limit_mercado = MagicMock(spec=SpendingLimit, category="mercado", amount=500.0)
    limit_lazer = MagicMock(spec=SpendingLimit, category="lazer", amount=0.0)

    spent_by_category = {
        "mercado": 200.0,
        "farmacia": 80.0,  # Sem limite cadastrado
    }
    cat_map = {
        "mercado": "Supermercado",
        "lazer": "Lazer & Cultura",
        "farmacia": "Farmácia",
    }

    balances = balance_service._build_balances(
        limits=[limit_mercado, limit_lazer],
        spent_by_category=spent_by_category,
        cat_map=cat_map,
    )

    balance_dict = {b.category: b for b in balances}

    # Categoria com limite e gasto
    mercado = balance_dict["mercado"]
    assert mercado.category_display_name == "Supermercado"
    assert mercado.limit == 500.0
    assert mercado.spent == 200.0
    assert mercado.available == 300.0
    assert mercado.percentage_used == 40.0

    # Categoria com limite zero e sem gasto
    lazer = balance_dict["lazer"]
    assert lazer.limit == 0.0
    assert lazer.spent == 0.0
    assert lazer.available == 0.0
    assert lazer.percentage_used == 100.0

    # Categoria sem limite com gasto
    farmacia = balance_dict["farmacia"]
    assert farmacia.category_display_name == "Farmácia"
    assert farmacia.limit == 0.0
    assert farmacia.spent == 80.0
    assert farmacia.available == -80.0
    assert farmacia.percentage_used == 100.0


@pytest.mark.asyncio
async def test_resolve_pm_invoice_period_with_reference_month(balance_service):
    pm = MagicMock(spec=PaymentMethod, key="nubank")
    balance_service.inv_service.get_invoice_dates = AsyncMock(
        return_value=(date(2025, 3, 1), date(2025, 3, 31))
    )

    start_d, end_d = await balance_service._resolve_pm_invoice_period(
        pm=pm, reference_month="2025-03", today=date(2025, 3, 15)
    )

    assert start_d == date(2025, 3, 1)
    assert end_d == date(2025, 3, 31)
    balance_service.inv_service.get_invoice_dates.assert_awaited_once_with(pm, "2025-03")


@pytest.mark.asyncio
async def test_resolve_pm_invoice_period_shifts_next_month_when_today_past_end(balance_service):
    pm = MagicMock(spec=PaymentMethod, key="nubank")

    # Primeira chamada: ciclo do mês corrente (fechou em 10/05)
    # Segunda chamada: ciclo do próximo mês (mês seguinte)
    balance_service.inv_service.get_invoice_dates = AsyncMock(
        side_effect=[
            (date(2025, 4, 11), date(2025, 5, 10)),
            (date(2025, 5, 11), date(2025, 6, 10)),
        ]
    )

    today = date(2025, 5, 20)  # > 10/05, logo fatura fechou e deve ir pro próximo mês
    start_d, end_d = await balance_service._resolve_pm_invoice_period(
        pm=pm, reference_month=None, today=today
    )

    assert start_d == date(2025, 5, 11)
    assert end_d == date(2025, 6, 10)
    assert balance_service.inv_service.get_invoice_dates.await_count == 2


@pytest.mark.asyncio
async def test_resolve_pm_invoice_period_shifts_prev_month_when_today_before_start(balance_service):
    pm = MagicMock(spec=PaymentMethod, key="nubank")

    balance_service.inv_service.get_invoice_dates = AsyncMock(
        side_effect=[
            (date(2025, 5, 11), date(2025, 6, 10)),
            (date(2025, 4, 11), date(2025, 5, 10)),
        ]
    )

    today = date(2025, 5, 5)  # < 11/05
    start_d, end_d = await balance_service._resolve_pm_invoice_period(
        pm=pm, reference_month=None, today=today
    )

    assert start_d == date(2025, 4, 11)
    assert end_d == date(2025, 5, 10)
    assert balance_service.inv_service.get_invoice_dates.await_count == 2


@pytest.mark.asyncio
async def test_get_balance_full_flow():
    limit_repo = MagicMock(spec=SpendingLimitRepository)
    spent_repo = MagicMock(spec=SpentRepository)
    category_repo = MagicMock(spec=CategoryRepository)
    pm_repo = MagicMock(spec=PaymentMethodRepository)
    inv_service = MagicMock(spec=InvoiceService)

    limit_mercado = MagicMock(spec=SpendingLimit, category="mercado", amount=1000.0)
    limit_repo.list = AsyncMock(return_value=([limit_mercado], 1))

    pm_card = MagicMock(spec=PaymentMethod, key="cartao_itau")
    pm_repo.list = AsyncMock(return_value=([pm_card], 1))

    inv_service.get_invoice_dates = AsyncMock(return_value=(date(2025, 5, 1), date(2025, 5, 31)))

    spent1 = MagicMock(spec=Spent, category="mercado", amount=350.0)
    spent_repo.list_by_multiple_periods = AsyncMock(return_value=([spent1], 1))

    cat_category = MagicMock(key="mercado", display_name="Supermercado")
    category_repo.list = AsyncMock(return_value=([cat_category], 1))

    service = BalanceService(
        limit_repo=limit_repo,
        spent_repo=spent_repo,
        category_repo=category_repo,
        pm_repo=pm_repo,
        inv_service=inv_service,
    )

    balances = await service.get_balance(reference_month="2025-05")

    assert len(balances) == 1
    balance = balances[0]
    assert balance.category == "mercado"
    assert balance.category_display_name == "Supermercado"
    assert balance.limit == 1000.0
    assert balance.spent == 350.0
    assert balance.available == 650.0
    assert balance.percentage_used == 35.0


def test_get_balance_service_dependency():
    mock_db = MagicMock()
    service = get_balance_service(mock_db)

    assert isinstance(service.limit_repo, SpendingLimitRepository)
    assert isinstance(service.spent_repo, SpentRepository)
    assert isinstance(service.category_repo, CategoryRepository)
    assert isinstance(service.pm_repo, PaymentMethodRepository)
    assert isinstance(service.inv_service, InvoiceService)
