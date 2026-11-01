from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubscriptionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50, description="Category key")
    amount: float
    payment_method: str | None = Field(default=None, max_length=50)
    payment_type: str = Field(default="CREDIT", max_length=20)
    account_id: UUID | None = None
    credit_card_id: UUID | None = None
    is_active: bool = True

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str | None) -> str | None:
        return v.lower().strip() if v else None


class SubscriptionCreate(SubscriptionBase):
    created_at: datetime | None = None


class SubscriptionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    category: str | None = Field(None, min_length=1, max_length=50)
    amount: float | None = None
    payment_method: str | None = Field(None, max_length=50)
    payment_type: str | None = None
    account_id: UUID | None = None
    credit_card_id: UUID | None = None
    is_active: bool | None = None

    @field_validator("category")
    @classmethod
    def validate_category_update(cls, v: str | None) -> str | None:
        return v.lower().strip() if v else None

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method_update(cls, v: str | None) -> str | None:
        return v.lower().strip() if v else None


class SubscriptionResponse(SubscriptionBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
