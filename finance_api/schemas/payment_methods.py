from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentMethodBase(BaseModel):
    key: str = Field(
        ..., max_length=50, description="Unique identifier key for the payment method"
    )
    display_name: str = Field(
        ..., max_length=100, description="Human-readable display name"
    )


class PaymentMethodCreate(PaymentMethodBase): ...


class PaymentMethodUpdate(BaseModel):
    key: str | None = Field(None, max_length=50)
    display_name: str | None = Field(None, max_length=100)


class PaymentMethodResponse(PaymentMethodBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
