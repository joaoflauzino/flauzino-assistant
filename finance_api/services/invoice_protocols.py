"""Structural contracts for invoice-related service collaborators."""

from datetime import date
from typing import Protocol

from finance_api.models.payment_methods import PaymentMethod


class InvoicePeriodProviderProtocol(Protocol):
    """Contract for resolving the billing window of a credit card invoice."""

    async def get_billing_period(
        self,
        payment_method: PaymentMethod,
        reference_month: str,
    ) -> tuple[date, date]: ...
