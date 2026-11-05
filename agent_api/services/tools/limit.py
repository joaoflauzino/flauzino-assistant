"""Tool: register a spending limit."""

from langchain_core.tools import BaseTool, tool

from agent_api.core.decorators import handle_tool_errors
from agent_api.core.logger import get_logger
from agent_api.schemas.limit import LimitDetails
from agent_api.services.protocols import FinanceServiceProtocol, GraphServiceProtocol

logger = get_logger(__name__)


def build_cadastrar_limite(
    finance_service: FinanceServiceProtocol,
    graph_service: GraphServiceProtocol,
) -> BaseTool:
    """Builds the ``cadastrar_limite`` tool bound to ``finance_service``."""

    @tool
    @handle_tool_errors("cadastrar_limite")
    async def cadastrar_limite(
        categoria: str,
        valor: float,
    ) -> str:
        """Cadastra ou atualiza o limite de gastos para uma categoria confirmada pelo usuário.

        ATENÇÃO: Chame esta ferramenta APENAS após ter perguntado ao usuário e ele
        ter confirmado expressamente os dados do limite.
        """
        logger.info(f"Tool cadastrar_limite chamada: {categoria} -> R${valor}")
        details = LimitDetails(
            categoria=categoria,
            valor=valor,
        )
        result = await finance_service.save_limit(details)
        return f"Limite cadastrado com sucesso! Detalhes: {result}"

    return cadastrar_limite
