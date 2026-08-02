import base64
from typing import Optional

from fastapi import APIRouter, Query

from mcp_server.schemas.graphs import GraphImageResponse
from mcp_server.services import finance_service, graph_service

router = APIRouter(prefix="/graphs", tags=["graphs"])


@router.get("/balance", response_model=GraphImageResponse)
async def get_balance_graph(
    reference_month: Optional[str] = Query(None, description="Mês de referência (ex: '2026-07')"),
    mode: str = Query("saldo", description="'saldo' ou 'limites'"),
    categories: Optional[str] = Query(
        None, description="Categorias separadas por vírgula (ex: 'mercado,lazer')"
    ),
) -> GraphImageResponse:
    """Generates a balance bar chart and returns it as base64-encoded PNG."""
    cats_list = categories.split(",") if categories else None
    balances = await finance_service.fetch_balance(reference_month, cats_list)

    title_suffix = f" ({reference_month})" if reference_month else ""
    if mode == "saldo":
        title = f"Saldo Atual e Gastos (Stacked){title_suffix}"
    else:
        title = f"Limites Cadastrados{title_suffix}"

    img_bytes = await graph_service.generate_balance_bar_chart(balances, title, mode=mode)
    return GraphImageResponse(image_base64=base64.b64encode(img_bytes).decode("utf-8"))
