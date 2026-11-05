from dataclasses import dataclass
from uuid import UUID

from finance_api.repositories.protocols import (
    AccountRepositoryProtocol,
    CreditCardRepositoryProtocol,
)


@dataclass(frozen=True)
class ResolvedPaymentTarget:
    """Resolved relational target for a payment method."""

    account_id: UUID | None
    credit_card_id: UUID | None
    payment_type: str


@dataclass(frozen=True, slots=True)
class PaymentResolutionContext:
    """Inputs shared by every payment resolution step."""

    clean_key: str
    requested_payment_type: str | None
    card_repo: CreditCardRepositoryProtocol | None
    account_repo: AccountRepositoryProtocol | None
