from fastapi import APIRouter

from finance_api.core.service_dependencies import InvoiceServiceDep
from finance_api.schemas.invoices import (
    InvoiceResponse,
    UpdateClosingDateRequest,
    UpdateInvoiceDatesRequest,
)

router = APIRouter()


@router.get("/{reference_month}", response_model=list[InvoiceResponse])
async def list_invoices(
    reference_month: str,
    service: InvoiceServiceDep,
) -> list[InvoiceResponse]:
    return await service.list_previews(reference_month)


@router.put("/{payment_method_key}/{reference_month}/closing-date", response_model=InvoiceResponse)
async def update_closing_date(
    payment_method_key: str,
    reference_month: str,
    body: UpdateClosingDateRequest,
    service: InvoiceServiceDep,
) -> InvoiceResponse:
    return await service.update_closing_date(payment_method_key, reference_month, body.closing_date)


@router.put("/{payment_method_key}/{reference_month}", response_model=InvoiceResponse)
async def update_invoice(
    payment_method_key: str,
    reference_month: str,
    body: UpdateInvoiceDatesRequest,
    service: InvoiceServiceDep,
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
    service: InvoiceServiceDep,
) -> InvoiceResponse:
    return await service.mark_as_paid(payment_method_key, reference_month)


@router.post("/{payment_method_key}/{reference_month}/reopen", response_model=InvoiceResponse)
async def reopen_invoice(
    payment_method_key: str,
    reference_month: str,
    service: InvoiceServiceDep,
) -> InvoiceResponse:
    return await service.reopen_invoice(payment_method_key, reference_month)
