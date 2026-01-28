from pydantic import BaseModel, Field


class LimitDetails(BaseModel):
    category: str = Field(..., min_length=1, max_length=100)
    value: float = Field(..., gt=0)
