from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from finance_api.schemas.enums import CardEnum, NameEnum


class SpentBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=50, description="Category key")
    amount: float
    payment_method: str = Field(..., min_length=1, max_length=50)
    payment_owner: str = Field(..., min_length=1, max_length=50)
    location: str

    @field_validator("category", "payment_method", "payment_owner")
    @classmethod
    def validate_keys(cls, v: str) -> str:
        """Normalize keys to lowercase."""
        return v.lower().strip()


class SpentCreate(SpentBase): ...


class SpentUpdate(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    amount: Optional[float] = None
    payment_method: Optional[str] = Field(None, min_length=1, max_length=50)
    payment_owner: Optional[str] = Field(None, min_length=1, max_length=50)
    location: Optional[str] = None

    @field_validator("category", "payment_method", "payment_owner")
    @classmethod
    def validate_keys_update(cls, v: Optional[str]) -> Optional[str]:
        """Normalize keys to lowercase if provided."""
        return v.lower().strip() if v else None


class SpentResponse(SpentBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
