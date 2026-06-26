from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from finance_api.models.invoices import InvoiceStatus


class InvoiceBase(BaseModel):
    payment_method_key: str = Field(..., max_length=50)
    reference_month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="YYYY-MM format")
    real_closing_date: date
    real_due_date: date
    status: InvoiceStatus = Field(default=InvoiceStatus.OPEN)


class InvoiceCreate(InvoiceBase): ...


class InvoiceUpdate(BaseModel):
    real_closing_date: date | None = None
    real_due_date: date | None = None
    status: InvoiceStatus | None = None


class InvoiceResponse(InvoiceBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
