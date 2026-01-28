from pydantic import BaseModel, Field

from finance_api.schemas.enums import CategoryEnum


class LimitDetails(BaseModel):
    category: CategoryEnum = Field(..., description="Categoria do limite de gasto")
    value: float = Field(..., gt=0, description="Valor do limite")
