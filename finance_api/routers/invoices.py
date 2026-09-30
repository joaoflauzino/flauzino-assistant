from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.invoices import InvoiceRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.schemas.invoices import (
    InvoiceResponse,
    UpdateClosingDateRequest,
    UpdateInvoiceDatesRequest,
)
from finance_api.services.invoices import InvoiceService

router = APIRouter()


def get_invoice_service(db: AsyncSession = Depends(get_db)) -> InvoiceService:
    repo = InvoiceRepository(db)
    pm_repo = PaymentMethodRepository(db)
    return InvoiceService(repo, pm_repo)


@router.get("/{reference_month}", response_model=List[InvoiceResponse])
async def list_invoices(
    reference_month: str,
    service: InvoiceService = Depends(get_invoice_service),
) -> List[InvoiceResponse]:
    return await service.list_previews(reference_month)


@router.put("/{payment_method_key}/{reference_month}/closing-date", response_model=InvoiceResponse)
async def update_closing_date(
    payment_method_key: str,
    reference_month: str,
    body: UpdateClosingDateRequest,
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    return await service.update_closing_date(payment_method_key, reference_month, body.closing_date)


@router.put("/{payment_method_key}/{reference_month}", response_model=InvoiceResponse)
async def update_invoice(
    payment_method_key: str,
    reference_month: str,
    body: UpdateInvoiceDatesRequest,
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    return await service.update_invoice_dates(
        payment_method_key,
        reference_month,
        closing_date=body.closing_date,
        due_date=body.due_date,
        status=body.status,
    )


@router.post("/{payment_method_key}/{reference_month}/pay", response_model=InvoiceResponse)
async def mark_invoice_as_paid(
    payment_method_key: str,
    reference_month: str,
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    return await service.mark_as_paid(payment_method_key, reference_month)


@router.post("/{payment_method_key}/{reference_month}/reopen", response_model=InvoiceResponse)
async def reopen_invoice(
    payment_method_key: str,
    reference_month: str,
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    return await service.reopen_invoice(payment_method_key, reference_month)
