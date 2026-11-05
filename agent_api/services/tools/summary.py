"""Tool: monthly financial summary."""

from langchain_core.tools import BaseTool, tool

from agent_api.core.decorators import handle_tool_errors
from agent_api.core.logger import get_logger
from agent_api.services.protocols import FinanceServiceProtocol, GraphServiceProtocol

logger = get_logger(__name__)


def build_consultar_balanco_mensal(
    finance_service: FinanceServiceProtocol,
    graph_service: GraphServiceProtocol,
) -> BaseTool:
    """Builds the ``consultar_balanco_mensal`` tool bound to ``finance_service``."""

    @tool
    @handle_tool_errors("consultar_balanco_mensal")
    async def consultar_balanco_mensal(
        mes_referencia: str | None = None,
    ) -> str | dict:
        """Consulta o balanço mensal integrado (entradas/receitas vs saídas/gastos, saldo líquido e taxa de economia/poupança).

        Args:
            mes_referencia: Mês de referência no formato 'YYYY-MM' (ex: '2026-08').
                            Deixe vazio ou None para consultar o mês atual.
        """
        logger.info(f"Tool consultar_balanco_mensal chamada para mes_referencia={mes_referencia}")
        summary = await finance_service.get_monthly_summary(reference_month=mes_referencia)
        if not summary:
            return "Não foi possível obter o resumo do balanço mensal para o período solicitado."
        return summary

    return consultar_balanco_mensal
