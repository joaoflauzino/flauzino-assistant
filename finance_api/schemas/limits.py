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
    category: str | None = Field(None, min_length=1, max_length=50)
    amount: float | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        """Normalize category to lowercase if provided."""
        return v.lower().strip() if v else None


class SpendingLimitResponse(SpendingLimitBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class CategoryBalance(BaseModel):
    category: str
    category_display_name: str
    limit: float
    spent: float
    available: float
    percentage_used: float

    model_config = ConfigDict(from_attributes=True)
