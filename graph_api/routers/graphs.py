import base64

from fastapi import APIRouter

from graph_api.schemas.graphs import (
    BalanceBarChartRequest,
    ExpensePieChartRequest,
    GraphImageResponse,
)
from graph_api.services import graph_service

router = APIRouter(prefix="/graphs", tags=["graphs"])


@router.post("/bar", response_model=GraphImageResponse)
async def generate_bar_graph(payload: BalanceBarChartRequest) -> GraphImageResponse:
    """Gera um gráfico de barras comparativo (gastos vs limite ou limites cadastrados)."""
    title = payload.title
    if not title:
        title = "Limites Cadastrados" if payload.mode == "limites" else "Saldo Atual e Gastos"

    balances_dicts = [item.model_dump() for item in payload.balances]
    img_bytes = await graph_service.generate_balance_bar_chart(
        balances_dicts, title, mode=payload.mode
    )
    return GraphImageResponse(image_base64=base64.b64encode(img_bytes).decode("utf-8"))


@router.post("/pie", response_model=GraphImageResponse)
async def generate_pie_graph(payload: ExpensePieChartRequest) -> GraphImageResponse:
    """Gera um gráfico de pizza mostrando a distribuição de gastos por categoria."""
    title = payload.title or "Distribuição de Gastos por Categoria"

    balances_dicts = [item.model_dump() for item in payload.balances]
    img_bytes = await graph_service.generate_expense_pie_chart(balances_dicts, title)
    return GraphImageResponse(image_base64=base64.b64encode(img_bytes).decode("utf-8"))
