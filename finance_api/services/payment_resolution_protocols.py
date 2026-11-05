"""Structural contracts for payment relation resolution.

The context dataclass lives here because it is the input contract shared by the
resolution steps; the concrete steps live in ``payment_resolution_steps``.
"""

from dataclasses import dataclass
from typing import Protocol

from finance_api.repositories.protocols import (
    AccountRepositoryProtocol,
    CreditCardRepositoryProtocol,
)
from finance_api.schemas.payment_resolution import ResolvedPaymentTarget


@dataclass(frozen=True, slots=True)
class PaymentResolutionContext:
    """Inputs shared by every payment resolution step."""

    clean_key: str
    requested_payment_type: str | None
    card_repo: CreditCardRepositoryProtocol | None
    account_repo: AccountRepositoryProtocol | None


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
