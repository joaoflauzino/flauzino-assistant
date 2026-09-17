from unittest.mock import AsyncMock

import pytest
from langgraph.types import Command

from agent_api.schemas.limit import LimitDetails
from agent_api.schemas.spending import SpendingDetails
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
def tools_map(mock_finance_service, mock_graph_service):
    tools = create_agent_tools(mock_finance_service, mock_graph_service)
    return {t.name: t for t in tools}


@pytest.mark.asyncio
async def test_consultar_saldos_success(tools_map, mock_finance_service):
    mock_finance_service.get_balances.return_value = [{"category": "mercado", "available": 500.0}]
    tool = tools_map["consultar_saldos"]
    result = await tool.ainvoke({"categorias": ["mercado"]})

    assert result == [{"category": "mercado", "available": 500.0}]
    mock_finance_service.get_balances.assert_awaited_once_with(categories=["mercado"])


@pytest.mark.asyncio
async def test_consultar_saldos_empty(tools_map, mock_finance_service):
    mock_finance_service.get_balances.return_value = []
    tool = tools_map["consultar_saldos"]
    result = await tool.ainvoke({"categorias": None})

    assert "Nenhum limite ou gasto encontrado" in result


@pytest.mark.asyncio
async def test_registrar_gasto_success(tools_map, mock_finance_service):
    mock_finance_service.save_spent.return_value = {"id": 10, "status": "created"}
    tool = tools_map["registrar_gasto"]
    result = await tool.ainvoke(
        {
            "categoria": "mercado",
            "valor": 120.50,
            "item_comprado": "Arroz e feijão",
            "metodo_pagamento": "pix",
            "local_compra": "Supermercado X",
        }
    )

    assert "Gasto registrado com sucesso" in result
    mock_finance_service.save_spent.assert_awaited_once()
    saved_details = mock_finance_service.save_spent.call_args[0][0]
    assert isinstance(saved_details, SpendingDetails)
    assert saved_details.categoria == "mercado"
    assert saved_details.valor == 120.50


@pytest.mark.asyncio
async def test_cadastrar_limite_success(tools_map, mock_finance_service):
    mock_finance_service.save_limit.return_value = {"id": 1, "category": "lazer", "amount": 300.0}
    tool = tools_map["cadastrar_limite"]
    result = await tool.ainvoke({"categoria": "lazer", "valor": 300.0})

    assert "Limite cadastrado com sucesso" in result
    mock_finance_service.save_limit.assert_awaited_once()
    saved_limit = mock_finance_service.save_limit.call_args[0][0]
    assert isinstance(saved_limit, LimitDetails)
    assert saved_limit.categoria == "lazer"
    assert saved_limit.valor == 300.0


@pytest.mark.asyncio
async def test_gerar_grafico_success(tools_map, mock_finance_service, mock_graph_service):
    mock_finance_service.get_balances.return_value = [{"category": "mercado", "available": 500.0}]
    mock_graph_service.generate_chart.return_value = "fake_b64_chart"
    tool = tools_map["gerar_grafico"]

    result = await tool.ainvoke(
        {
            "name": "gerar_grafico",
            "args": {"tipo": "pie", "categorias": ["mercado"], "modo": "saldo"},
            "id": "call_123",
            "type": "tool_call",
        }
    )

    assert isinstance(result, Command)
    assert result.update["image_base64"] == "fake_b64_chart"
    assert len(result.update["messages"]) == 1
    assert result.update["messages"][0].tool_call_id == "call_123"
    mock_graph_service.generate_chart.assert_awaited_once_with(
        chart_type="pie",
        balances=[{"category": "mercado", "available": 500.0}],
        mode="saldo",
    )


@pytest.mark.asyncio
async def test_gerar_grafico_sem_dados(tools_map, mock_finance_service):
    mock_finance_service.get_balances.return_value = []
    tool = tools_map["gerar_grafico"]

    result = await tool.ainvoke(
        {
            "name": "gerar_grafico",
            "args": {"tipo": "bar", "categorias": None, "modo": "saldo"},
            "id": "call_456",
            "type": "tool_call",
        }
    )

    content = result.content if hasattr(result, "content") else str(result)
    assert "Não foram encontrados limites ou gastos" in content
