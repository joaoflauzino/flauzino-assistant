from pydantic import BaseModel, Field


class SpendingDetails(BaseModel):
    categoria: str = Field(..., description="Categoria do gasto")
    valor: float = Field(..., description="Valor do gasto")
    metodo_pagamento: str = Field(
        ..., description="Nome do cartão de crédito utilizado (ex: itau, c6, xp)"
    )
    proprietário: str = Field(..., description="Nome do proprietário do gasto")
    local_compra: str = Field(..., description="Local onde a compra foi realizada")
