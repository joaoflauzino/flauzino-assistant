from pydantic import BaseModel, Field


class LimitDetails(BaseModel):
    category: str = Field(..., description="Categoria do limite de gasto")
    value: float = Field(..., gt=0, description="Valor do limite")
