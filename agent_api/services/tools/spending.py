"""Tool: register a confirmed expense."""

from langchain_core.tools import BaseTool, tool

from agent_api.core.decorators import handle_tool_errors
from agent_api.core.logger import get_logger
from agent_api.schemas.spending import SpendingDetails
from agent_api.services.protocols import FinanceServiceProtocol, GraphServiceProtocol

logger = get_logger(__name__)


def build_registrar_gasto(
    finance_service: FinanceServiceProtocol,
    graph_service: GraphServiceProtocol,
) -> BaseTool:
    """Builds the ``registrar_gasto`` tool bound to ``finance_service``."""

    @tool
    @handle_tool_errors("registrar_gasto")
    async def registrar_gasto(
        categoria: str,
        valor: float,
        item_comprado: str,
        metodo_pagamento: str,
        local_compra: str,
    ) -> str:
        """Registra uma despesa/gasto confirmado pelo usuário.

        ATENÇÃO: Chame esta ferramenta APENAS após ter perguntado ao usuário e ele
        ter confirmado expressamente os dados do gasto (ex: 'Sim', 'Pode registrar').
        """
        logger.info(
            f"Tool registrar_gasto chamada: {item_comprado}, R${valor} ({categoria}) via {metodo_pagamento}"
        )
        details = SpendingDetails(
            categoria=categoria,
            valor=valor,
            item_comprado=item_comprado,
            metodo_pagamento=metodo_pagamento,
            local_compra=local_compra,
        )
        result = await finance_service.save_spent(details)
        return f"Gasto registrado com sucesso no sistema financeiro! Detalhes: {result}"

    return registrar_gasto
