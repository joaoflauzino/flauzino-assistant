from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DashboardMode(str, Enum):
    CIVIL_MONTH = "CIVIL_MONTH"
    INVOICES = "INVOICES"


class SpentBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=50, description="Category key")
    amount: float
    item_bought: str = Field(..., min_length=1, max_length=50)
    payment_method: Optional[str] = Field(default=None, max_length=50)
    payment_type: str = Field(
        default="CREDIT", description="CREDIT, DEBIT, PIX, CASH, TRANSFER, OTHER"
    )
    account_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None
    location: str

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: Optional[str]) -> Optional[str]:
        return v.lower().strip() if v else None

    @field_validator("payment_type", mode="before")
    @classmethod
    def validate_payment_type(cls, v: Any) -> str:
        if not isinstance(v, str):
            return "CREDIT"
        return v

    @field_validator("account_id", "credit_card_id", mode="before")
    @classmethod
    def validate_uuid_or_none(cls, v: Any) -> Optional[UUID]:
        if isinstance(v, UUID):
            return v
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                return None
        return None


class SpentCreate(SpentBase):
    is_installment: Optional[bool] = False
    current_installment: Optional[int] = Field(default=None, ge=1)
    total_installments: Optional[int] = Field(default=None, ge=2)
    created_at: Optional[datetime] = None


class SpentUpdate(BaseModel):
    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    amount: Optional[float] = None
    item_bought: Optional[str] = Field(default=None, min_length=1, max_length=50)
    payment_method: Optional[str] = Field(default=None, max_length=50)
    payment_type: Optional[str] = None
    account_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None
    location: Optional[str] = None
    installment_id: Optional[UUID] = None
    current_installment: Optional[int] = None
    total_installments: Optional[int] = None

    @field_validator("category")
    @classmethod
    def validate_category_update(cls, v: Optional[str]) -> Optional[str]:
        return v.lower().strip() if v else None

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method_update(cls, v: Optional[str]) -> Optional[str]:
        return v.lower().strip() if v else None


class SpentResponse(SpentBase):
    id: UUID
    created_at: datetime
    installment_id: Optional[UUID] = None
    current_installment: Optional[int] = None
    total_installments: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
