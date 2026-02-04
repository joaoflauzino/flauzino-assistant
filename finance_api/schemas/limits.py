from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SpendingLimitBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=50, description="Category key")
    amount: float

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Normalize category to lowercase."""
        return v.lower().strip()


class SpendingLimitCreate(SpendingLimitBase): ...


class SpendingLimitUpdate(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    amount: Optional[float] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Normalize category to lowercase if provided."""
        return v.lower().strip() if v else None


class SpendingLimitResponse(SpendingLimitBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
