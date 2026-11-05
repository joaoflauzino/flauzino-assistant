"""Tool: generate a financial chart attached to the reply."""

from typing import Annotated, Literal

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command

from agent_api.core.decorators import handle_tool_errors
from agent_api.core.logger import get_logger
from agent_api.services.protocols import FinanceServiceProtocol, GraphServiceProtocol

logger = get_logger(__name__)

CHART_WITHOUT_DATA_MESSAGE = (
    "Não foram encontrados limites ou gastos para gerar o gráfico solicitado."
)
CHART_SUCCESS_MESSAGE = "[Gráfico gerado com sucesso e exibido ao usuário]"


def build_chart_command(image_base64: str, tool_call_id: str) -> Command:
    """Builds the command that attaches the chart to the agent state and to the reply."""
    return Command(
        update={
            "image_base64": image_base64,
            "messages": [ToolMessage(content=CHART_SUCCESS_MESSAGE, tool_call_id=tool_call_id)],
        }
    )


def build_gerar_grafico(
    finance_service: FinanceServiceProtocol,
    graph_service: GraphServiceProtocol,
) -> BaseTool:
    """Builds the ``gerar_grafico`` tool bound to both services."""

    @tool
    @handle_tool_errors("gerar_grafico")
    async def gerar_grafico(
        tipo: Literal["bar", "pie"],
        tool_call_id: Annotated[str, InjectedToolCallId],
        categorias: list[str] | None = None,
        modo: Literal["saldo", "gastos"] = "saldo",
        mes_referencia: str | None = None,
    ) -> Command | str:
        """Gera um gráfico visual com base nos dados financeiros e anexa à resposta.

        Args:
            tipo: 'pie' para gráfico de pizza (proporção de gastos) ou 'bar' para gráfico de barras (comparativo).
            categorias: Lista opcional de categorias específicas para exibir no gráfico.
            modo: 'saldo' (comparativo limites vs gastos) ou 'gastos' (apenas gastos). Padrão 'saldo'.
            mes_referencia: Mês de referência no formato 'YYYY-MM' (ex: '2026-08').
                            Deixe vazio ou None para gerar o gráfico com o ciclo/mês ativo atual.
        """
        logger.info(
            f"Tool gerar_grafico chamada: tipo={tipo}, modo={modo}, categorias={categorias}, mes_referencia={mes_referencia}"
        )
        balances = await finance_service.get_balances(
            categories=categorias, reference_month=mes_referencia
        )
        if not balances:
            return CHART_WITHOUT_DATA_MESSAGE

        image_b64 = await graph_service.generate_chart(
            chart_type=tipo,
            balances=balances,
            mode=modo,
        )
        return build_chart_command(image_b64, tool_call_id)

    return gerar_grafico
