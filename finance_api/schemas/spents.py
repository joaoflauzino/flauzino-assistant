from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DashboardMode(StrEnum):
    CIVIL_MONTH = "CIVIL_MONTH"
    INVOICES = "INVOICES"


class SpentBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=50, description="Category key")
    amount: float
    item_bought: str = Field(..., min_length=1, max_length=50)
    payment_method: str | None = Field(default=None, max_length=50)
    payment_type: str = Field(
        default="CREDIT", description="CREDIT, DEBIT, PIX, CASH, TRANSFER, OTHER"
    )
    account_id: UUID | None = None
    credit_card_id: UUID | None = None
    location: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str | None) -> str | None:
        return v.lower().strip() if v else None

    @field_validator("payment_type", mode="before")
    @classmethod
    def validate_payment_type(cls, v: Any) -> str:
        if not isinstance(v, str):
            return "CREDIT"
        return v

    @field_validator("account_id", "credit_card_id", mode="before")
    @classmethod
    def validate_uuid_or_none(cls, v: Any) -> UUID | None:
        if isinstance(v, UUID):
            return v
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                return None
        return None


class SpentCreate(SpentBase):
    is_installment: bool | None = False
    current_installment: int | None = Field(default=None, ge=1)
    total_installments: int | None = Field(default=None, ge=2)
    created_at: datetime | None = None


class SpentUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=50)
    amount: float | None = None
    item_bought: str | None = Field(default=None, min_length=1, max_length=50)
    payment_method: str | None = Field(default=None, max_length=50)
    payment_type: str | None = None
    account_id: UUID | None = None
    credit_card_id: UUID | None = None
    location: str | None = None
    installment_id: UUID | None = None
    current_installment: int | None = None
    total_installments: int | None = None

    @field_validator("category")
    @classmethod
    def validate_category_update(cls, v: str | None) -> str | None:
        return v.lower().strip() if v else None

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method_update(cls, v: str | None) -> str | None:
        return v.lower().strip() if v else None


class SpentResponse(SpentBase):
    id: UUID
    created_at: datetime
    installment_id: UUID | None = None
    current_installment: int | None = None
    total_installments: int | None = None

    model_config = ConfigDict(from_attributes=True)
