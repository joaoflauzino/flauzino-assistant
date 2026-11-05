"""Tool: consult running balances and limits."""

from langchain_core.tools import BaseTool, tool

from agent_api.core.decorators import handle_tool_errors
from agent_api.core.logger import get_logger
from agent_api.schemas.finance import BalancePayload
from agent_api.services.protocols import FinanceServiceProtocol, GraphServiceProtocol

logger = get_logger(__name__)


def build_consultar_saldos(
    finance_service: FinanceServiceProtocol,
    graph_service: GraphServiceProtocol,
) -> BaseTool:
    """Builds the ``consultar_saldos`` tool bound to ``finance_service``."""

    @tool
    @handle_tool_errors("consultar_saldos")
    async def consultar_saldos(
        categorias: list[str] | None = None,
        mes_referencia: str | None = None,
    ) -> str | list[BalancePayload]:
        """Consulta os saldos e limites de gastos da família.

        Args:
            categorias: Lista opcional de categorias a filtrar (ex: ['mercado', 'combustivel']).
                        Deixe vazio ou None para consultar todas as categorias disponíveis.
            mes_referencia: Mês de referência no formato 'YYYY-MM' (ex: '2026-08').
                            Deixe vazio ou None para consultar o ciclo/mês ativo atual.
        """
        logger.info(
            f"Tool consultar_saldos chamada para categorias={categorias}, mes_referencia={mes_referencia}"
        )
        balances = await finance_service.get_balances(
            categories=categorias, reference_month=mes_referencia
        )
        if not balances:
            return "Nenhum limite ou gasto encontrado para as categorias informadas."
        return balances

    return consultar_saldos
