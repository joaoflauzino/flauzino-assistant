from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ResolvedPaymentTarget:
    """Resolved relational target for a payment method."""

    account_id: UUID | None
    credit_card_id: UUID | None
    payment_type: str
