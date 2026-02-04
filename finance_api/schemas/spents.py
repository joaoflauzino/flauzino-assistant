from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from finance_api.schemas.enums import CardEnum, NameEnum


class SpentBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=50, description="Category key")
    amount: float
    payment_method: CardEnum
    payment_owner: NameEnum
    location: str

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Normalize category to lowercase."""
        return v.lower().strip()


class SpentCreate(SpentBase): ...


class SpentUpdate(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    amount: Optional[float] = None
    payment_method: Optional[CardEnum] = None
    payment_owner: Optional[NameEnum] = None
    location: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Normalize category to lowercase if provided."""
        return v.lower().strip() if v else None


class SpentResponse(SpentBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
