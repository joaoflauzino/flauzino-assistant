from pydantic import BaseModel, Field


class SpendingDetails(BaseModel):
    categoria: str | None = Field(
        None, description="Categoria do gasto (ex: comer fora, mercado)"
    )
    valor: float | None = Field(None, description="Valor do gasto")
    metodo_pagamento: str | None = Field(
        None, description="Método de pagamento (ex: cartão c6, dinheiro)"
    )
    local_compra: str | None = Field(
        None, description="Local onde a compra foi realizada"
    )
