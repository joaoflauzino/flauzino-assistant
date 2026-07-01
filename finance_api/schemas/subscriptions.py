from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubscriptionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50, description="Category key")
    amount: float
    payment_method: str = Field(..., min_length=1, max_length=50)
    is_active: bool = True

    @field_validator("category", "payment_method")
    @classmethod
    def validate_keys(cls, v: str) -> str:
        """Normalize keys to lowercase."""
        return v.lower().strip()


class SubscriptionCreate(SubscriptionBase):
    created_at: Optional[datetime] = None


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    amount: Optional[float] = None
    payment_method: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None

    @field_validator("category", "payment_method")
    @classmethod
    def validate_keys_update(cls, v: Optional[str]) -> Optional[str]:
        return v.lower().strip() if v else None


class SubscriptionResponse(SubscriptionBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
