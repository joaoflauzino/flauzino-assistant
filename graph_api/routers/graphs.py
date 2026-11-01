import base64

from fastapi import APIRouter

from graph_api.schemas.graphs import (
    BalanceBarChartRequest,
    ChartMode,
    ExpensePieChartRequest,
    GraphImageResponse,
)
from graph_api.services.graph_service import GraphRendererServiceDep

router = APIRouter(prefix="/graphs", tags=["graphs"])


@router.post("/bar", response_model=GraphImageResponse)
async def generate_bar_graph(
    payload: BalanceBarChartRequest,
    renderer: GraphRendererServiceDep,
) -> GraphImageResponse:
    """Gera um gráfico de barras comparativo (gastos vs limite ou limites cadastrados)."""
    title = payload.title
    if not title:
        title = (
            "Limites Cadastrados" if payload.mode == ChartMode.LIMITES else "Saldo Atual e Gastos"
        )

    balances_dicts = [item.model_dump() for item in payload.balances]
    img_bytes = await renderer.render(
        balances=balances_dicts,
        title=title,
        mode=payload.mode,
    )
    return GraphImageResponse(image_base64=base64.b64encode(img_bytes).decode("utf-8"))


@router.post("/pie", response_model=GraphImageResponse)
async def generate_pie_graph(
    payload: ExpensePieChartRequest,
    renderer: GraphRendererServiceDep,
) -> GraphImageResponse:
    """Gera um gráfico de pizza mostrando a distribuição de gastos por categoria."""
    title = payload.title or "Distribuição de Gastos por Categoria"

    balances_dicts = [item.model_dump() for item in payload.balances]
    img_bytes = await renderer.render(
        balances=balances_dicts,
        title=title,
        mode=ChartMode.PIE,
    )
    return GraphImageResponse(image_base64=base64.b64encode(img_bytes).decode("utf-8"))
