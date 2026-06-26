from datetime import date
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from finance_api.core.database import get_db
from finance_api.repositories.invoices import InvoiceRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.services.invoices import InvoiceService
from finance_api.schemas.invoices import InvoiceResponse

router = APIRouter()


class UpdateClosingDateRequest(BaseModel):
    closing_date: date


@router.get("/{reference_month}", response_model=List[InvoiceResponse])
async def list_invoices(
    reference_month: str, db: AsyncSession = Depends(get_db)
) -> List[InvoiceResponse]:
    repo = InvoiceRepository(db)
    pm_repo = PaymentMethodRepository(db)
    service = InvoiceService(repo, pm_repo)
    return await service.list_previews(reference_month)


@router.put("/{payment_method_key}/{reference_month}/closing-date", response_model=InvoiceResponse)
async def update_closing_date(
    payment_method_key: str,
    reference_month: str,
    body: UpdateClosingDateRequest,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    repo = InvoiceRepository(db)
    pm_repo = PaymentMethodRepository(db)
    service = InvoiceService(repo, pm_repo)
    return await service.update_closing_date(payment_method_key, reference_month, body.closing_date)
