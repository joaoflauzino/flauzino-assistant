from typing import Annotated, Literal

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command

from agent_api.core.decorators import handle_tool_errors
from agent_api.core.logger import get_logger
from agent_api.schemas.limit import LimitDetails
from agent_api.schemas.spending import SpendingDetails
from agent_api.services.finance import FinanceService
from agent_api.services.graph import GraphService

logger = get_logger(__name__)


def create_agent_tools(
    finance_service: FinanceService,
    graph_service: GraphService,
) -> list[BaseTool]:
    """Factory creating LangChain tools with injected services."""

    @tool
    @handle_tool_errors("consultar_saldos")
    async def consultar_saldos(categorias: list[str] | None = None) -> str | list[dict]:
        """Consulta os saldos e limites de gastos atuais da família.

        Args:
            categorias: Lista opcional de categorias a filtrar (ex: ['mercado', 'combustivel']).
                        Deixe vazio ou None para consultar todas as categorias disponíveis.
        """
        logger.info(f"Tool consultar_saldos chamada para categorias: {categorias}")
        balances = await finance_service.get_balances(categories=categorias)
        if not balances:
            return "Nenhum limite ou gasto encontrado para as categorias informadas."
        return balances

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

    @tool
    @handle_tool_errors("gerar_grafico")
    async def gerar_grafico(
        tipo: Literal["bar", "pie"],
        tool_call_id: Annotated[str, InjectedToolCallId],
        categorias: list[str] | None = None,
        modo: Literal["saldo", "gastos"] = "saldo",
    ) -> Command | str:
        """Gera um gráfico visual com base nos dados financeiros e anexa à resposta.

        Args:
            tipo: 'pie' para gráfico de pizza (proporção de gastos) ou 'bar' para gráfico de barras (comparativo).
            categorias: Lista opcional de categorias específicas para exibir no gráfico.
            modo: 'saldo' (comparativo limites vs gastos) ou 'gastos' (apenas gastos). Padrão 'saldo'.
        """
        logger.info(
            f"Tool gerar_grafico chamada: tipo={tipo}, modo={modo}, categorias={categorias}"
        )
        balances = await finance_service.get_balances(categories=categorias)
        if not balances:
            return "Não foram encontrados limites ou gastos para gerar o gráfico solicitado."

        image_b64 = await graph_service.generate_chart(
            chart_type=tipo,
            balances=balances,
            mode=modo,
        )
        return Command(
            update={
                "image_base64": image_b64,
                "messages": [
                    ToolMessage(
                        content="[Gráfico gerado com sucesso e exibido ao usuário]",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )

    return [
        consultar_saldos,
        registrar_gasto,
        cadastrar_limite,
        gerar_grafico,
    ]
