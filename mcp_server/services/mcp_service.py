import base64
from typing import Any

from mcp.types import ImageContent, TextContent, Tool

from mcp_server.core.mcp import mcp_server
from mcp_server.services import finance_service, graph_service


@mcp_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Registers available MCP tools for graph generation."""
    return [
        Tool(
            name="plot_category_balance",
            description=(
                "Gera um gráfico de barras comparando os Limites cadastrados com os Gastos "
                "atuais por categoria. Use isso quando o usuário perguntar sobre saldos ou limites."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "reference_month": {
                        "type": "string",
                        "description": "Mês de referência (ex: '2026-07'). Opcional.",
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Lista opcional de nomes de categorias para filtrar "
                            "(ex: ['mercado', 'lazer']). Se não informado, retorna todas."
                        ),
                    },
                    "mode": {
                        "type": "string",
                        "description": (
                            "Opcional. 'saldo' para mostrar gastos e disponíveis empilhados, "
                            "ou 'limites' para mostrar apenas as barras de limite. "
                            "Padrão é 'saldo'."
                        ),
                    },
                },
            },
        ),
        Tool(
            name="plot_expense_pie_chart",
            description=(
                "Gera um gráfico de pizza mostrando a distribuição dos gastos por categoria. "
                "Use isso quando o usuário pedir análises visuais de onde está gastando mais."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "reference_month": {
                        "type": "string",
                        "description": "Mês de referência (ex: '2026-07'). Opcional.",
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Lista opcional de nomes de categorias para filtrar. "
                            "Se não informado, retorna todas."
                        ),
                    },
                },
            },
        ),
    ]


@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[ImageContent | TextContent]:
    """Routes MCP tool calls to the appropriate service functions."""
    args = arguments or {}
    ref_month = args.get("reference_month")
    categories = args.get("categories")
    mode = args.get("mode", "saldo")

    balances = await finance_service.fetch_balance(ref_month, categories)

    if not balances:
        return [
            TextContent(
                type="text",
                text=(
                    "Não encontrei limites cadastrados ou gastos para as categorias que você pediu. "
                    "Verifique se o nome está correto ou se houve algum registro neste mês."
                ),
            )
        ]

    title_suffix = f" ({ref_month})" if ref_month else ""

    if name == "plot_category_balance":
        if mode == "saldo":
            title = f"Saldo Atual e Gastos (Stacked){title_suffix}"
        else:
            title = f"Limites Cadastrados{title_suffix}"

        img_bytes = await graph_service.generate_balance_bar_chart(balances, title, mode=mode)
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return [ImageContent(type="image", data=b64, mimeType="image/png")]

    elif name == "plot_expense_pie_chart":
        img_bytes = await graph_service.generate_expense_pie_chart(
            balances, f"Distribuição de Gastos{title_suffix}"
        )
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return [ImageContent(type="image", data=b64, mimeType="image/png")]

    else:
        return [TextContent(type="text", text=f"Ferramenta desconhecida: {name}")]
