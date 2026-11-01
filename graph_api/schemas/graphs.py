from enum import StrEnum

from pydantic import BaseModel, Field


class ChartMode(StrEnum):
    SALDO = "saldo"
    LIMITES = "limites"
    PIE = "pie"


class CategoryBalanceItem(BaseModel):
    category_display_name: str
    limit: float = 0.0
    spent: float = 0.0
    available: float = 0.0


class BalanceBarChartRequest(BaseModel):
    balances: list[CategoryBalanceItem] = Field(
        ..., description="Lista de dados de saldos e limites por categoria"
    )
    title: str | None = Field(None, description="Título customizado do gráfico")
    mode: str = Field(ChartMode.SALDO, description="'saldo' ou 'limites'")


class ExpensePieChartRequest(BaseModel):
    balances: list[CategoryBalanceItem] = Field(
        ..., description="Lista de dados de gastos por categoria"
    )
    title: str | None = Field(None, description="Título customizado do gráfico")


class GraphImageResponse(BaseModel):
    """Response containing a base64-encoded graph image."""

    image_base64: str
