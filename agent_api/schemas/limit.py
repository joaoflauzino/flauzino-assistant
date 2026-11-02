from pydantic import BaseModel, Field, field_validator


class LimitDetails(BaseModel):
    categoria: str = Field(..., description="Categoria do limite de gasto")
    valor: float = Field(..., gt=0, description="Valor do limite")

    @field_validator("categoria")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        """Normalize the category key before validation and storage."""
        return value.lower().strip()
