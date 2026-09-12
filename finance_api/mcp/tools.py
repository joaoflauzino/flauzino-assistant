import base64
from typing import Annotated

import httpx
from mcp.server.fastmcp import Image
from pydantic import Field

from finance_api.core.database import AsyncSessionLocal
from finance_api.core.dependencies import get_balance_service, get_spent_service
from finance_api.core.logger import get_logger
from finance_api.mcp.server import mcp
from finance_api.repositories.categories import CategoryRepository
from finance_api.schemas.spents import SpentCreate
from finance_api.services.categories import CategoryService
from finance_api.settings import settings

logger = get_logger(__name__)


@mcp.tool()
async def get_category_balance(
    reference_month: Annotated[
        str | None,
        Field(
            description="Mês de referência no formato 'YYYY-MM' (ex: '2026-08'). Opcional; padrão é o mês atual."
        ),
    ] = None,
    categories: Annotated[
        list[str] | None,
        Field(
            description="Lista opcional de chaves de categorias para filtrar (ex: ['mercado', 'lazer'])."
        ),
    ] = None,
) -> list[dict]:
    """Consulta os saldos disponíveis, limites e gastos de cada categoria."""
    async with AsyncSessionLocal() as db:
        balance_service = get_balance_service(db)
        balances = await balance_service.get_balance(reference_month=reference_month)

        result = [b.model_dump() for b in balances]
        if categories:
            cats_set = {c.lower().strip() for c in categories}
            result = [
                b
                for b in result
                if b["category"].lower() in cats_set
                or b["category_display_name"].lower() in cats_set
            ]
        return result


@mcp.tool()
async def create_spent(
    category: Annotated[
        str,
        Field(
            description="Chave da categoria do gasto (ex: 'alimentacao', 'mercado', 'transporte')."
        ),
    ],
    amount: Annotated[float, Field(description="Valor do gasto em reais.")],
    item_bought: Annotated[str, Field(description="Nome do item ou serviço comprado.")],
    payment_method: Annotated[
        str, Field(description="Método de pagamento utilizado (ex: 'nubank', 'itau', 'pix').")
    ],
    location: Annotated[str, Field(description="Local ou estabelecimento onde ocorreu a compra.")],
) -> dict:
    """Registra um novo gasto no sistema de finanças."""
    async with AsyncSessionLocal() as db:
        service = get_spent_service(db)

        spent_create = SpentCreate(
            category=category,
            amount=amount,
            item_bought=item_bought,
            payment_method=payment_method,
            location=location,
        )
        created = await service.create(spent_create)
        return created.model_dump(mode="json")


@mcp.tool()
async def list_categories() -> list[dict]:
    """Lista todas as categorias de gastos cadastradas no sistema."""
    async with AsyncSessionLocal() as db:
        repo = CategoryRepository(db)
        service = CategoryService(repo)
        items, _ = await service.list(page=1, size=100)
        return [item.model_dump(mode="json") for item in items]


@mcp.tool()
async def get_balance_chart(
    reference_month: Annotated[
        str | None,
        Field(description="Mês de referência (ex: '2026-08'). Opcional."),
    ] = None,
    mode: Annotated[
        str,
        Field(
            description="'saldo' para limites vs gastos empilhados, ou 'limites' apenas para barras de limites."
        ),
    ] = "saldo",
    categories: Annotated[
        list[str] | None,
        Field(description="Categorias opcionais a incluir no gráfico."),
    ] = None,
) -> Image:
    """Gera uma imagem de gráfico comparativo de saldos/gastos e retorna como imagem PNG."""
    balances = await get_category_balance(reference_month=reference_month, categories=categories)
    if not balances:
        raise ValueError("Nenhum dado encontrado para gerar o gráfico.")

    payload = {
        "balances": balances,
        "title": f"Saldos ({reference_month})" if reference_month else "Saldo Atual e Gastos",
        "mode": mode,
    }

    url = f"{settings.GRAPH_SERVICE_URL.rstrip('/')}/graphs/bar"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        img_bytes = base64.b64decode(data["image_base64"])
        return Image(data=img_bytes, format="png")
