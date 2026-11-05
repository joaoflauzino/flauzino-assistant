"""Structural contracts for payment relation resolution."""

from typing import Protocol

from finance_api.schemas.payment_resolution import (
    PaymentResolutionContext,
    ResolvedPaymentTarget,
)


class PaymentResolutionStep(Protocol):
    """Contract for a single step of the payment resolution chain."""

    async def resolve(self, ctx: PaymentResolutionContext) -> ResolvedPaymentTarget | None: ...


class PaymentResolutionServiceProtocol(Protocol):
    """Structural contract for resolving account/credit card relations."""

    async def resolve(
        self,
        payment_method_key: str | None,
        requested_payment_type: str | None = None,
        is_credit_card_hint: bool = False,
    ) -> ResolvedPaymentTarget: ...
