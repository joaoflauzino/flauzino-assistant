from unittest.mock import AsyncMock

import pytest

from agent_api.services.finance import FinanceService
from agent_api.services.graph import GraphService
from agent_api.services.tools import create_agent_tools


@pytest.fixture
def mock_finance_service():
    return AsyncMock(spec=FinanceService)


@pytest.fixture
def mock_graph_service():
    return AsyncMock(spec=GraphService)


@pytest.fixture
def tools(mock_finance_service, mock_graph_service):
    return create_agent_tools(mock_finance_service, mock_graph_service)


@pytest.mark.asyncio
async def test_tool_registrar_receita(tools, mock_finance_service):
    registrar_receita = next(t for t in tools if t.name == "registrar_receita")
    mock_finance_service.save_income.return_value = {"id": "inc-1", "amount": 4500.0}

    result = await registrar_receita.ainvoke(
        {
            "fonte": "Salário Mensal",
            "valor": 4500.0,
            "categoria": "salario",
            "metodo_recebimento": "itau_joao",
        }
    )

    assert "Receita registrada com sucesso" in result
    mock_finance_service.save_income.assert_awaited_once()


@pytest.mark.asyncio
async def test_tool_consultar_balanco_mensal(tools, mock_finance_service):
    consultar_balanco = next(t for t in tools if t.name == "consultar_balanco_mensal")
    mock_finance_service.get_monthly_summary.return_value = {
        "reference_month": "2026-08",
        "total_incomes": 8000.0,
        "total_spents": 4000.0,
        "net_balance": 4000.0,
    }

    result = await consultar_balanco.ainvoke({"mes_referencia": "2026-08"})

    assert isinstance(result, dict)
    assert result["net_balance"] == 4000.0
    mock_finance_service.get_monthly_summary.assert_awaited_once_with(reference_month="2026-08")
