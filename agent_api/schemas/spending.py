from pydantic import BaseModel, Field, field_validator


class SpendingDetails(BaseModel):
    categoria: str = Field(..., description="Categoria do gasto")
    valor: float = Field(..., description="Valor do gasto")
    metodo_pagamento: str = Field(
        ...,
        description="Método de pagamento utilizado. DEVE corresponder EXATAMENTE a uma das chaves válidas informadas. Não tente deduzir ou inventar (se houver ambiguidade, pergunte ao usuário qual é a opção correta).",
    )
    item_comprado: str = Field(..., description="Nome do item comprado")
    local_compra: str = Field(..., description="Local onde a compra foi realizada")

    @field_validator("categoria", "metodo_pagamento", "item_comprado", "local_compra")
    @classmethod
    def validate_keys_update(cls, v: str | None) -> str | None:
        """Normalize keys to lowercase if provided."""
        return v.lower().strip() if v else None
