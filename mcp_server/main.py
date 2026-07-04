import base64
import os
import httpx
import plotly.graph_objects as go
import plotly.express as px
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from typing import Optional, Any

from mcp.server import Server
from mcp.types import Tool, ImageContent, TextContent
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.responses import Response

FINANCE_SERVICE_URL = os.getenv("FINANCE_SERVICE_URL", "http://finance_api:8000")

mcp_server = Server("graph-generator")


async def fetch_balance(reference_month: str = None, categories: list[str] = None) -> list[dict]:
    url = f"{FINANCE_SERVICE_URL}/limits/balance"
    if reference_month:
        url += f"?reference_month={reference_month}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

        if categories and "todas as categorias" not in [c.lower() for c in categories]:
            filtered_data = []
            for b in data:
                cat_name = b["category_display_name"].lower()
                cat_key = b["category"].lower()
                if any(c.lower() in cat_name or c.lower() in cat_key for c in categories):
                    filtered_data.append(b)
            return filtered_data

        return data


def generate_balance_bar_chart(balances: list[dict], title: str, mode: str = "saldo") -> bytes:
    categories = []
    limits = []
    spents = []
    availables = []

    for b in balances:
        categories.append(b["category_display_name"])
        limits.append(b["limit"])
        spents.append(b["spent"])
        availables.append(max(0, b["available"]))  # Prevent negative stacked bar

    if mode == "limites":
        fig = go.Figure(
            data=[
                go.Bar(
                    name="Limite",
                    x=categories,
                    y=limits,
                    marker_color="cornflowerblue",
                    text=[f"R$ {v:.2f}" for v in limits],
                    textposition="auto",
                )
            ]
        )
        fig.update_layout(
            title=title, yaxis_title="Valor (R$)", xaxis_title="Categoria", template="plotly_white"
        )
    else:  # mode == "saldo"
        fig = go.Figure(
            data=[
                go.Bar(
                    name="Gasto",
                    x=categories,
                    y=spents,
                    marker_color="tomato",
                    text=[f"R$ {v:.2f}" if v > 0 else "" for v in spents],
                    textposition="inside",
                    insidetextanchor="middle",
                ),
                go.Bar(
                    name="Saldo Disponível",
                    x=categories,
                    y=availables,
                    marker_color="lightgreen",
                    text=[f"R$ {v:.2f}" if v > 0 else "" for v in availables],
                    textposition="inside",
                    insidetextanchor="middle",
                ),
            ]
        )
        fig.update_layout(
            barmode="stack",
            title=title,
            yaxis_title="Valor (R$)",
            xaxis_title="Categoria",
            template="plotly_white",
            uniformtext_minsize=10,
            uniformtext_mode="show",
        )

    # Needs kaleido
    return fig.to_image(format="png", width=800, height=500)


def generate_expense_pie_chart(balances: list[dict], title: str) -> bytes:
    categories = []
    spents = []

    for b in balances:
        if b["spent"] > 0:
            categories.append(b["category_display_name"])
            spents.append(b["spent"])

    if not categories:
        # Empty chart
        fig = go.Figure()
        fig.update_layout(title="Nenhum gasto registrado", template="plotly_white")
        return fig.to_image(format="png", width=800, height=500)

    fig = px.pie(values=spents, names=categories, title=title, hole=0.3)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(template="plotly_white")
    return fig.to_image(format="png", width=800, height=500)


@mcp_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="plot_category_balance",
            description="Gera um gráfico de barras comparando os Limites cadastrados com os Gastos atuais por categoria. Use isso quando o usuário perguntar sobre saldos ou limites.",
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
                        "description": "Lista opcional de nomes de categorias para filtrar (ex: ['mercado', 'lazer']). Se não informado, retorna todas.",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Opcional. 'saldo' para mostrar gastos e disponíveis empilhados, ou 'limites' para mostrar apenas as barras de limite. Padrão é 'saldo'.",
                    },
                },
            },
        ),
        Tool(
            name="plot_expense_pie_chart",
            description="Gera um gráfico de pizza mostrando a distribuição dos gastos por categoria. Use isso quando o usuário pedir análises visuais de onde está gastando mais.",
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
                        "description": "Lista opcional de nomes de categorias para filtrar. Se não informado, retorna todas.",
                    },
                },
            },
        ),
    ]


@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[ImageContent | TextContent]:
    args = arguments or {}
    ref_month = args.get("reference_month")
    categories = args.get("categories")
    mode = args.get("mode", "saldo")

    try:
        balances = await fetch_balance(ref_month, categories)

        if not balances:
            return [
                TextContent(
                    type="text",
                    text="Nenhum dado encontrado para gerar o gráfico com as categorias informadas. Por favor informe o usuário que essas categorias não existem ou não possuem limites cadastrados.",
                )
            ]

        title_suffix = f" ({ref_month})" if ref_month else ""

        if name == "plot_category_balance":
            if mode == "saldo":
                title = f"Saldo Atual e Gastos (Stacked){title_suffix}"
            else:
                title = f"Limites Cadastrados{title_suffix}"

            img_bytes = generate_balance_bar_chart(balances, title, mode=mode)
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            return [ImageContent(type="image", data=b64, mimeType="image/png")]

        elif name == "plot_expense_pie_chart":
            img_bytes = generate_expense_pie_chart(
                balances, f"Distribuição de Gastos{title_suffix}"
            )
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            return [ImageContent(type="image", data=b64, mimeType="image/png")]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"Erro ao gerar gráfico: {str(e)}")]


app = FastAPI(title="MCP Graph Server")

# We will expose REST for telegram bot.

# We will expose REST for telegram bot.


@app.get("/graphs/balance")
async def get_balance_graph(
    reference_month: Optional[str] = None, mode: str = "saldo", categories: Optional[str] = None
):
    try:
        cats_list = categories.split(",") if categories else None
        balances = await fetch_balance(reference_month, cats_list)
        if not balances:
            return JSONResponse(status_code=404, content={"message": "No data"})

        title_suffix = f" ({reference_month})" if reference_month else ""
        if mode == "saldo":
            title = f"Saldo Atual e Gastos (Stacked){title_suffix}"
        else:
            title = f"Limites Cadastrados{title_suffix}"

        img_bytes = generate_balance_bar_chart(balances, title, mode=mode)
        return JSONResponse({"image_base64": base64.b64encode(img_bytes).decode("utf-8")})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


# Full correct implementation of MCP Server-Sent Events with standard library
sse = SseServerTransport("/messages/")


@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())
    return Response()


app.mount("/messages/", sse.handle_post_message)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
