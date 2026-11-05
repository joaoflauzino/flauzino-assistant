from typing import cast
from unittest.mock import AsyncMock

import pytest

from agent_api.schemas.finance import BalancePayload
from agent_api.services.agent import AgentService
from agent_api.services.clients.finance import FinanceService
from agent_api.services.clients.graph import GraphService
from agent_api.services.protocols import FinanceServiceProtocol, GraphServiceProtocol
from agent_api.services.tools.registry import create_agent_tools


class StructuralFinanceFake:
    """Implements only the operations the tools actually consume."""

    async def get_balances(
        self,
        categories: list[str] | None = None,
        reference_month: str | None = None,
    ) -> list[BalancePayload]:
        return [
            {
                "category": "mercado",
                "category_display_name": "Mercado",
                "limit": 1000.0,
                "spent": 500.0,
                "available": 500.0,
                "percentage_used": 50.0,
            }
        ]


class StructuralGraphFake:
    async def generate_chart(
        self,
        chart_type: str,
        balances: list[BalancePayload],
        mode: str = "saldo",
        title: str | None = None,
    ) -> str:
        return "chart_base64"


def test_concrete_clients_satisfy_service_contracts() -> None:
    client = AsyncMock()
    finance_service: FinanceServiceProtocol = FinanceService(client=client)
    graph_service: GraphServiceProtocol = GraphService(client=client)

    assert finance_service is not graph_service


def test_agent_service_builds_tools_from_structural_contracts() -> None:
    finance = cast(FinanceServiceProtocol, StructuralFinanceFake())
    graph = cast(GraphServiceProtocol, StructuralGraphFake())

    tools = create_agent_tools(finance, graph)

    assert {tool.name for tool in tools} == {
        "consultar_saldos",
        "registrar_gasto",
        "registrar_receita",
        "consultar_balanco_mensal",
        "cadastrar_limite",
        "gerar_grafico",
    }


def test_agent_service_accepts_structural_contracts() -> None:
    finance = cast(FinanceServiceProtocol, StructuralFinanceFake())
    graph = cast(GraphServiceProtocol, StructuralGraphFake())

    service = AgentService(llm=AsyncMock(), finance_service=finance, graph_service=graph)

    assert service.finance_service is finance
    assert service.graph_service is graph


@pytest.mark.asyncio
async def test_structural_graph_fake_is_used_by_the_tool() -> None:
    tools = create_agent_tools(
        cast(FinanceServiceProtocol, StructuralFinanceFake()),
        cast(GraphServiceProtocol, StructuralGraphFake()),
    )
    graph_tool = next(tool for tool in tools if tool.name == "gerar_grafico")

    result = await graph_tool.ainvoke(
        {
            "name": "gerar_grafico",
            "args": {"tipo": "pie", "modo": "saldo"},
            "id": "call_structural",
            "type": "tool_call",
        }
    )

    assert result.update["image_base64"] == "chart_base64"
