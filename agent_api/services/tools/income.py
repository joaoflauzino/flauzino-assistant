"""Tool: register a confirmed income."""

from langchain_core.tools import BaseTool, tool

from agent_api.core.decorators import handle_tool_errors
from agent_api.core.logger import get_logger
from agent_api.schemas.income import IncomeDetails
from agent_api.services.finance import FinanceService
from agent_api.services.graph import GraphService

logger = get_logger(__name__)


def build_registrar_receita(
    finance_service: FinanceService,
    graph_service: GraphService,
) -> BaseTool:
    """Builds the ``registrar_receita`` tool bound to ``finance_service``."""

    @tool
    @handle_tool_errors("registrar_receita")
    async def registrar_receita(
        fonte: str,
        valor: float,
        categoria: str,
        metodo_recebimento: str | None = None,
    ) -> str:
        """Registra uma receita ou entrada financeira confirmada pelo usuário.

        ATENÇÃO: Chame esta ferramenta APENAS após ter perguntado ao usuário e ele
        ter confirmado expressamente os dados da receita (ex: 'Sim', 'Pode registrar').
        """
        logger.info(
            f"Tool registrar_receita chamada: {fonte}, R${valor} ({categoria}) via {metodo_recebimento}"
        )
        details = IncomeDetails(
            fonte=fonte,
            valor=valor,
            categoria=categoria,
            metodo_recebimento=metodo_recebimento,
        )
        result = await finance_service.save_income(details)
        return f"Receita registrada com sucesso no sistema financeiro! Detalhes: {result}"

    return registrar_receita
