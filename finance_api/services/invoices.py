import calendar
from datetime import date, datetime
from typing import List, Tuple
from uuid import UUID
from dateutil.relativedelta import relativedelta
import holidays

from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError
from finance_api.core.logger import get_logger
from finance_api.models.invoices import InvoiceStatus
from finance_api.models.payment_methods import PaymentMethod
from finance_api.repositories.invoices import InvoiceRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.schemas.invoices import InvoiceCreate, InvoiceResponse, InvoiceUpdate

logger = get_logger(__name__)


def compute_real_date(reference_month: str, target_day: int) -> date:
    year, month = map(int, reference_month.split("-"))
    _, last_day = calendar.monthrange(year, month)
    day = min(target_day, last_day)

    target_date = date(year, month, day)
    br_holidays = holidays.BR()

    while target_date.weekday() >= 5 or target_date in br_holidays:
        target_date += relativedelta(days=1)

    return target_date


def get_due_reference_month(reference_month: str, closing_day: int, due_day: int) -> str:
    """Resolve the reference month for the invoice due date.

    If the due day is less than or equal to the closing day (e.g. closes on the 28th and
    due on the 5th), the due date falls into the subsequent month.
    """
    if due_day <= closing_day:
        year, month = map(int, reference_month.split("-"))
        due_date_ref = date(year, month, 1) + relativedelta(months=1)
        return due_date_ref.strftime("%Y-%m")
    return reference_month


class InvoiceService:
    def __init__(self, repo: InvoiceRepository, pm_repo: PaymentMethodRepository):
        self.repo = repo
        self.pm_repo = pm_repo

    @handle_service_errors
    async def get_invoice_dates(
        self, payment_method: PaymentMethod, reference_month: str
    ) -> Tuple[date, date]:
        """Calculates real_closing_date and real_due_date for a given month and payment method.

        Checks for an existing override in `invoices` table first.
        If not found, computes using payment_method's closing_day and due_day.
        """
        if not payment_method.is_credit_card:
            raise ValueError(f"Payment method {payment_method.key} is not a credit card.")

        invoice = await self.repo.get_by_payment_method_and_month(
            payment_method.key, reference_month
        )
        if invoice:
            return invoice.real_closing_date, invoice.real_due_date

        closing_day = payment_method.closing_day or 1
        due_day = payment_method.due_day or 1

        due_reference_month = get_due_reference_month(reference_month, closing_day, due_day)

        real_closing = compute_real_date(reference_month, closing_day)
        real_due = compute_real_date(due_reference_month, due_day)

        return real_closing, real_due

    @handle_service_errors
    async def list_previews(self, reference_month: str) -> List[InvoiceResponse]:
        """Lists invoices for all credit cards for a given reference month.

        Returns persisted invoices or computes preview based on payment methods.
        """
        credit_cards = await self.pm_repo.list_credit_cards()
        invoices = await self.repo.list_by_month(reference_month)
        invoices_map = {inv.payment_method_key: inv for inv in invoices}

        result = []
        for cc in credit_cards:
            if cc.key in invoices_map:
                result.append(InvoiceResponse.model_validate(invoices_map[cc.key]))
            else:
                closing_day = cc.closing_day or 1
                due_day = cc.due_day or 1
                due_reference_month = get_due_reference_month(reference_month, closing_day, due_day)
                real_closing = compute_real_date(reference_month, closing_day)
                real_due = compute_real_date(due_reference_month, due_day)

                result.append(
                    InvoiceResponse(
                        id=UUID("00000000-0000-0000-0000-000000000000"),
                        payment_method_key=cc.key,
                        credit_card_id=cc.id,
                        reference_month=reference_month,
                        real_closing_date=real_closing,
                        real_due_date=real_due,
                        status=InvoiceStatus.OPEN,
                        created_at=datetime.now(),
                    )
                )

        return result

    @handle_service_errors
    async def update_invoice_dates(
        self,
        payment_method_key: str,
        reference_month: str,
        closing_date: date | None = None,
        due_date: date | None = None,
        status: InvoiceStatus | None = None,
    ) -> InvoiceResponse:
        """Updates or creates an invoice with custom closing_date, due_date, and/or status."""
        pm = await self.pm_repo.get_by_key(payment_method_key)
        if not pm or not pm.is_credit_card:
            raise EntityNotFoundError(f"Cartão de crédito {payment_method_key} não encontrado")

        invoice = await self.repo.get_by_payment_method_and_month(
            payment_method_key, reference_month
        )
        if invoice:
            update_data = InvoiceUpdate()
            if closing_date is not None:
                update_data.real_closing_date = closing_date
            if due_date is not None:
                update_data.real_due_date = due_date
            if status is not None:
                update_data.status = status
            if not invoice.credit_card_id and pm.id:
                update_data.credit_card_id = pm.id
            updated = await self.repo.update(invoice.id, update_data)
            return InvoiceResponse.model_validate(updated)

        closing_d = pm.closing_day or (closing_date.day if closing_date else 1)
        due_d = pm.due_day or (due_date.day if due_date else 1)
        due_ref_month = get_due_reference_month(reference_month, closing_d, due_d)

        final_closing = closing_date or compute_real_date(reference_month, closing_d)
        final_due = due_date or compute_real_date(due_ref_month, due_d)
        final_status = status or InvoiceStatus.OPEN

        new_inv = InvoiceCreate(
            payment_method_key=payment_method_key,
            credit_card_id=pm.id,
            reference_month=reference_month,
            real_closing_date=final_closing,
            real_due_date=final_due,
            status=final_status,
        )
        created = await self.repo.create(new_inv)
        return InvoiceResponse.model_validate(created)

    @handle_service_errors
    async def update_closing_date(
        self, payment_method_key: str, reference_month: str, closing_date: date
    ) -> InvoiceResponse:
        return await self.update_invoice_dates(
            payment_method_key, reference_month, closing_date=closing_date
        )

    @handle_service_errors
    async def mark_as_paid(self, payment_method_key: str, reference_month: str) -> InvoiceResponse:
        """Marks an invoice as PAID, creating it if it was only a preview."""
        return await self.update_invoice_dates(
            payment_method_key, reference_month, status=InvoiceStatus.PAID
        )

    @handle_service_errors
    async def reopen_invoice(
        self, payment_method_key: str, reference_month: str
    ) -> InvoiceResponse:
        """Reopens an invoice (sets status to OPEN), creating it if it was only a preview."""
        return await self.update_invoice_dates(
            payment_method_key, reference_month, status=InvoiceStatus.OPEN
        )
