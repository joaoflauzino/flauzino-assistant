from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubscriptionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50, description="Category key")
    amount: float
    payment_method: Optional[str] = Field(default=None, max_length=50)
    payment_type: str = Field(default="CREDIT", max_length=20)
    account_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None
    is_active: bool = True

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: Optional[str]) -> Optional[str]:
        return v.lower().strip() if v else None


class SubscriptionCreate(SubscriptionBase):
    created_at: Optional[datetime] = None


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    amount: Optional[float] = None
    payment_method: Optional[str] = Field(None, max_length=50)
    payment_type: Optional[str] = None
    account_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None
    is_active: Optional[bool] = None

    @field_validator("category")
    @classmethod
    def validate_category_update(cls, v: Optional[str]) -> Optional[str]:
        return v.lower().strip() if v else None

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method_update(cls, v: Optional[str]) -> Optional[str]:
        return v.lower().strip() if v else None


class SubscriptionResponse(SubscriptionBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
