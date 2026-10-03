from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreditCardBase(BaseModel):
    key: str = Field(..., max_length=50, description="Unique key for the credit card")
    name: str = Field(..., max_length=100, description="Display name for the credit card")
    account_id: UUID = Field(..., description="ID of the parent account")
    closing_day: int = Field(..., ge=1, le=31, description="Day of month when statement closes")
    due_day: int = Field(..., ge=1, le=31, description="Day of month when payment is due")
    credit_limit: float = Field(default=0.0, ge=0.0, description="Total credit limit")


class CreditCardCreate(CreditCardBase):
    pass


class CreditCardUpdate(BaseModel):
    key: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, max_length=100)
    account_id: UUID | None = None
    closing_day: int | None = Field(default=None, ge=1, le=31)
    due_day: int | None = Field(default=None, ge=1, le=31)
    credit_limit: float | None = Field(default=None, ge=0.0)


class CreditCardResponse(CreditCardBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
