from pydantic import BaseModel, Field, field_validator


class IncomeDetails(BaseModel):
    fonte: str = Field(
        ..., description="Fonte ou descrição da receita (ex: 'Salário', 'Pix de Maria')"
    )
    valor: float = Field(..., gt=0, description="Valor da receita")
    categoria: str = Field(..., description="Categoria da receita")
    metodo_recebimento: str | None = Field(
        default=None,
        description="Conta ou método onde foi recebido (ex: 'itau_joao', 'nubank_joao', 'pix_joao').",
    )

    @field_validator("categoria", "metodo_recebimento")
    @classmethod
    def validate_keys(cls, v: str | None) -> str | None:
        """Normalize keys to lowercase if provided."""
        return v.lower().strip() if v else None
