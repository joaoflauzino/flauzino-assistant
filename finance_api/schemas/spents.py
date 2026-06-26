from datetime import datetime
from typing import Optional
from uuid import UUID

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DashboardMode(str, Enum):
    CIVIL_MONTH = "CIVIL_MONTH"
    INVOICES = "INVOICES"


class SpentBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=50, description="Category key")
    amount: float
    item_bought: str = Field(..., min_length=1, max_length=50)
    payment_method: str = Field(..., min_length=1, max_length=50)
    payment_owner: str = Field(..., min_length=1, max_length=50)
    location: str

    @field_validator("category", "payment_method", "payment_owner")
    @classmethod
    def validate_keys(cls, v: str) -> str:
        """Normalize keys to lowercase."""
        return v.lower().strip()


class SpentCreate(SpentBase):
    is_installment: Optional[bool] = False
    current_installment: Optional[int] = Field(None, ge=1)
    total_installments: Optional[int] = Field(None, ge=2)
    created_at: Optional[datetime] = None


class SpentUpdate(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    amount: Optional[float] = None
    item_bought: Optional[str] = Field(None, min_length=1, max_length=50)
    payment_method: Optional[str] = Field(None, min_length=1, max_length=50)
    payment_owner: Optional[str] = Field(None, min_length=1, max_length=50)
    location: Optional[str] = None
    installment_id: Optional[UUID] = None
    current_installment: Optional[int] = None
    total_installments: Optional[int] = None

    @field_validator("category", "payment_method", "payment_owner")
    @classmethod
    def validate_keys_update(cls, v: Optional[str]) -> Optional[str]:
        """Normalize keys to lowercase if provided."""
        return v.lower().strip() if v else None


class SpentResponse(SpentBase):
    id: UUID
    created_at: datetime
    installment_id: Optional[UUID] = None
    current_installment: Optional[int] = None
    total_installments: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
