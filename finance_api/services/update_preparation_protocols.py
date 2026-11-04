"""Structural contracts for the shared update-preparation steps."""

from typing import Protocol
from uuid import UUID

from finance_api.schemas.payment_resolution import ResolvedPaymentTarget


class PaymentResolutionServiceProtocol(Protocol):
    """Structural contract for resolving account/credit card relations."""

    async def resolve(
        self,
        payment_method_key: str | None,
        requested_payment_type: str | None = None,
        is_credit_card_hint: bool = False,
    ) -> ResolvedPaymentTarget: ...


class PaymentTargetPayload(Protocol):
    """Update payload that can receive the resolved payment relations."""

    payment_method: str | None
    payment_type: str | None
    account_id: UUID | None
    credit_card_id: UUID | None


class UpdatePreparationStep[T](Protocol):
    """Structural contract for a single preparation step of an update payload."""

    async def prepare(self, data: T) -> None: ...
