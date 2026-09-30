from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentMethodBase(BaseModel):
    key: str = Field(..., max_length=50, description="Unique identifier key for the payment method")
    display_name: str = Field(..., max_length=100, description="Human-readable display name")
    is_credit_card: bool = Field(
        default=False, description="Indicates if this payment method is a credit card"
    )
    closing_day: int | None = Field(
        default=None, ge=1, le=31, description="Day of the month the invoice closes"
    )
    due_day: int | None = Field(
        default=None, ge=1, le=31, description="Day of the month the invoice is due"
    )

    @field_validator("closing_day", "due_day", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


class PaymentMethodCreate(PaymentMethodBase): ...


class PaymentMethodUpdate(BaseModel):
    key: str | None = Field(default=None, max_length=50)
    display_name: str | None = Field(default=None, max_length=100)
    is_credit_card: bool | None = None
    closing_day: int | None = Field(default=None, ge=1, le=31)
    due_day: int | None = Field(default=None, ge=1, le=31)

    @field_validator("closing_day", "due_day", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


class PaymentMethodResponse(PaymentMethodBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
