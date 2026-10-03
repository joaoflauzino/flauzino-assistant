from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from finance_api.models.invoices import InvoiceStatus


class InvoiceBase(BaseModel):
    payment_method_key: str = Field(..., max_length=50)
    credit_card_id: Optional[UUID] = None
    reference_month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="YYYY-MM format")
    real_closing_date: date
    real_due_date: date
    status: InvoiceStatus = Field(default=InvoiceStatus.OPEN)

    @field_validator("credit_card_id", mode="before")
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


class InvoiceCreate(InvoiceBase): ...


class InvoiceUpdate(BaseModel):
    credit_card_id: Optional[UUID] = None
    real_closing_date: date | None = None
    real_due_date: date | None = None
    status: InvoiceStatus | None = None

    @field_validator("credit_card_id", mode="before")
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


class UpdateClosingDateRequest(BaseModel):
    closing_date: date


class UpdateInvoiceDatesRequest(BaseModel):
    closing_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[InvoiceStatus] = None


class InvoiceResponse(InvoiceBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
