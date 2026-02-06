from pydantic import BaseModel, Field, field_validator


class LimitDetails(BaseModel):
    categoria: str = Field(..., description="Categoria do limite de gasto")
    valor: float = Field(..., gt=0, description="Valor do limite")


@field_validator("categoria", "valor")
@classmethod
def validate_keys_update(cls, v: str | None) -> str | None:
    """Normalize keys to lowercase if provided."""
    return v.lower().strip() if v else None
