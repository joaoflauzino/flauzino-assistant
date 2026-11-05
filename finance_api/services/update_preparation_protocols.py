"""Structural contracts for the shared update-preparation steps."""

from typing import Protocol
from uuid import UUID


class PaymentTargetPayload(Protocol):
    """Update payload that can receive the resolved payment relations."""

    payment_method: str | None
    payment_type: str | None
    account_id: UUID | None
    credit_card_id: UUID | None


class UpdatePreparationStep[T](Protocol):
    """Structural contract for a single preparation step of an update payload."""

    async def prepare(self, data: T) -> None: ...
