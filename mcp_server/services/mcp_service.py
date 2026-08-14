from typing import Annotated

from pydantic import Field
from mcp.server.fastmcp import Image

from mcp_server.core.mcp import mcp
from mcp_server.services import finance_service, graph_service


@mcp.tool(structured_output=False)
async def plot_category_balance(
    reference_month: Annotated[
        str | None, Field(description="Mês de referência (ex: '2026-07'). Opcional.")
    ] = None,
    categories: Annotated[
        list[str] | None,
        Field(
            description=(
                "Lista opcional de nomes de categorias para filtrar "
                "(ex: ['mercado', 'lazer']). Se não informado, retorna todas."
            )
        ),
    ] = None,
    mode: Annotated[
        str,
        Field(
            description=(
                "Opcional. 'saldo' para mostrar gastos e disponíveis empilhados, "
                "ou 'limites' para mostrar apenas as barras de limite. Padrão é 'saldo'."
            )
        ),
    ] = "saldo",
) -> str | Image:
    """Gera um gráfico de barras comparando os Limites cadastrados com os Gastos atuais por categoria.

    Use isso quando o usuário perguntar sobre saldos ou limites.
    """
    balances = await finance_service.fetch_balance(reference_month, categories)

    if not balances:
        return (
            "Não encontrei limites cadastrados ou gastos para as categorias que você pediu. "
            "Verifique se o nome está correto ou se houve algum registro neste mês."
        )

    title_suffix = f" ({reference_month})" if reference_month else ""
    if mode == "saldo":
        title = f"Saldo Atual e Gastos (Stacked){title_suffix}"
    else:
        title = f"Limites Cadastrados{title_suffix}"

    img_bytes = await graph_service.generate_balance_bar_chart(balances, title, mode=mode)
    return Image(data=img_bytes, format="png")


@mcp.tool(structured_output=False)
async def plot_expense_pie_chart(
    reference_month: Annotated[
        str | None, Field(description="Mês de referência (ex: '2026-07'). Opcional.")
    ] = None,
    categories: Annotated[
        list[str] | None,
        Field(
            description=(
                "Lista opcional de nomes de categorias para filtrar. "
                "Se não informado, retorna todas."
            )
        ),
    ] = None,
) -> str | Image:
    """Gera um gráfico de pizza mostrando a distribuição dos gastos por categoria.

    Use isso quando o usuário pedir análises visuais de onde está gastando mais.
    """
    balances = await finance_service.fetch_balance(reference_month, categories)

    if not balances:
        return (
            "Não encontrei limites cadastrados ou gastos para as categorias que você pediu. "
            "Verifique se o nome está correto ou se houve algum registro neste mês."
        )

    title_suffix = f" ({reference_month})" if reference_month else ""
    img_bytes = await graph_service.generate_expense_pie_chart(
        balances, f"Distribuição de Gastos{title_suffix}"
    )
    return Image(data=img_bytes, format="png")
