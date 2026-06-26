from datetime import date, datetime
from typing import List, Tuple
from uuid import UUID
import calendar
from dateutil.relativedelta import relativedelta
import holidays

from finance_api.models.invoices import InvoiceStatus
from finance_api.models.payment_methods import PaymentMethod
from finance_api.repositories.invoices import InvoiceRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.schemas.invoices import InvoiceCreate, InvoiceUpdate, InvoiceResponse
from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError
from finance_api.core.logger import get_logger

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


class InvoiceService:
    def __init__(self, repo: InvoiceRepository, pm_repo: PaymentMethodRepository):
        self.repo = repo
        self.pm_repo = pm_repo

    @handle_service_errors
    async def get_invoice_dates(
        self, payment_method: PaymentMethod, reference_month: str
    ) -> Tuple[date, date]:
        if not payment_method.is_credit_card or not payment_method.closing_day:
            year, month = map(int, reference_month.split("-"))
            _, last_day = calendar.monthrange(year, month)
            return date(year, month, 1), date(year, month, last_day)

        invoice = await self.repo.get_by_payment_method_and_month(
            payment_method.key, reference_month
        )
        if invoice:
            current_closing = invoice.real_closing_date
        else:
            current_closing = compute_real_date(reference_month, payment_method.closing_day)

        year, month = map(int, reference_month.split("-"))
        prev_month_date = date(year, month, 1) - relativedelta(months=1)
        prev_reference_month = prev_month_date.strftime("%Y-%m")

        prev_invoice = await self.repo.get_by_payment_method_and_month(
            payment_method.key, prev_reference_month
        )
        if prev_invoice:
            prev_closing = prev_invoice.real_closing_date
        else:
            prev_closing = compute_real_date(prev_reference_month, payment_method.closing_day)

        start_date = prev_closing + relativedelta(days=1)
        return start_date, current_closing

    @handle_service_errors
    async def list_previews(self, reference_month: str) -> List[InvoiceResponse]:
        payment_methods, _ = await self.pm_repo.list(page=1, size=1000)
        saved_invoices = await self.repo.list_by_month(reference_month)
        saved_map = {inv.payment_method_key: inv for inv in saved_invoices}

        results = []
        for pm in payment_methods:
            if not pm.is_credit_card or not pm.closing_day or not pm.due_day:
                continue

            if pm.key in saved_map:
                inv = saved_map[pm.key]
                results.append(InvoiceResponse.model_validate(inv))
            else:
                real_closing = compute_real_date(reference_month, pm.closing_day)
                real_due = compute_real_date(reference_month, pm.due_day)

                results.append(
                    InvoiceResponse(
                        id=UUID("00000000-0000-0000-0000-000000000000"),
                        payment_method_key=pm.key,
                        reference_month=reference_month,
                        real_closing_date=real_closing,
                        real_due_date=real_due,
                        status=InvoiceStatus.OPEN,
                        created_at=datetime.now(),
                    )
                )
        return results

    @handle_service_errors
    async def update_closing_date(
        self, payment_method_key: str, reference_month: str, closing_date: date
    ) -> InvoiceResponse:
        invoice = await self.repo.get_by_payment_method_and_month(
            payment_method_key, reference_month
        )
        if invoice:
            updated = await self.repo.update(
                invoice.id, InvoiceUpdate(real_closing_date=closing_date)
            )
            return InvoiceResponse.model_validate(updated)

        pm = await self.pm_repo.get_by_key(payment_method_key)
        if not pm or not pm.is_credit_card:
            raise EntityNotFoundError(f"Credit card {payment_method_key} not found")

        real_due = compute_real_date(reference_month, pm.due_day or 1)

        new_inv = InvoiceCreate(
            payment_method_key=payment_method_key,
            reference_month=reference_month,
            real_closing_date=closing_date,
            real_due_date=real_due,
            status=InvoiceStatus.OPEN,
        )
        created = await self.repo.create(new_inv)
        return InvoiceResponse.model_validate(created)
