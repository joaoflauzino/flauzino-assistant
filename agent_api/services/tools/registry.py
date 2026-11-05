"""Factory registry that assembles every agent tool."""

from collections.abc import Callable

from langchain_core.tools import BaseTool

from agent_api.services.protocols import FinanceServiceProtocol, GraphServiceProtocol
from agent_api.services.tools.balance import build_consultar_saldos
from agent_api.services.tools.graph import build_gerar_grafico
from agent_api.services.tools.income import build_registrar_receita
from agent_api.services.tools.limit import build_cadastrar_limite
from agent_api.services.tools.spending import build_registrar_gasto
from agent_api.services.tools.summary import build_consultar_balanco_mensal

ToolBuilder = Callable[[FinanceServiceProtocol, GraphServiceProtocol], BaseTool]

TOOL_BUILDERS: tuple[ToolBuilder, ...] = (
    build_consultar_saldos,
    build_registrar_gasto,
    build_registrar_receita,
    build_consultar_balanco_mensal,
    build_cadastrar_limite,
    build_gerar_grafico,
)


def create_agent_tools(
    finance_service: FinanceServiceProtocol,
    graph_service: GraphServiceProtocol,
) -> list[BaseTool]:
    """Factory creating LangChain tools with injected services."""
    return [build(finance_service, graph_service) for build in TOOL_BUILDERS]
