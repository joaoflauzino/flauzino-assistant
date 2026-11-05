"""Domain service that resolves payment relations (account and/or credit card)."""

from collections.abc import Sequence

from finance_api.repositories.protocols import (
    AccountRepositoryProtocol,
    CreditCardRepositoryProtocol,
)
from finance_api.schemas.payment_resolution import (
    PaymentResolutionContext,
    ResolvedPaymentTarget,
)
from finance_api.services.payment_resolution_protocols import PaymentResolutionStep
from finance_api.services.payment_resolution_steps import (
    AccountPaymentStep,
    CreditCardPaymentStep,
)

DEFAULT_PAYMENT_TYPE = "DEBIT"
CREDIT_PAYMENT_TYPE = "CREDIT"


class PaymentResolutionService:
    """Resolves account and credit card relations from a payment method key."""

    def __init__(
        self,
        card_repo: CreditCardRepositoryProtocol | None = None,
        account_repo: AccountRepositoryProtocol | None = None,
    ) -> None:
        self._card_repo = card_repo
        self._account_repo = account_repo
        self._steps: Sequence[PaymentResolutionStep] = (
            CreditCardPaymentStep(),
            AccountPaymentStep(),
        )

    async def resolve(
        self,
        payment_method_key: str | None,
        requested_payment_type: str | None = None,
        is_credit_card_hint: bool = False,
    ) -> ResolvedPaymentTarget:
        """Resolves account_id, credit_card_id, and payment_type from a payment method key."""
        if not payment_method_key:
            return self._fallback(requested_payment_type, is_credit_card_hint)

        context = PaymentResolutionContext(
            clean_key=payment_method_key.strip().lower(),
            requested_payment_type=requested_payment_type,
            card_repo=self._card_repo,
            account_repo=self._account_repo,
        )
        for step in self._steps:
            target = await step.resolve(context)
            if target is not None:
                return target
        return self._fallback(requested_payment_type, is_credit_card_hint)

    def _fallback(
        self,
        requested_payment_type: str | None,
        is_credit_card_hint: bool,
    ) -> ResolvedPaymentTarget:
        if requested_payment_type:
            return ResolvedPaymentTarget(
                account_id=None,
                credit_card_id=None,
                payment_type=requested_payment_type,
            )
        return ResolvedPaymentTarget(
            account_id=None,
            credit_card_id=None,
            payment_type=CREDIT_PAYMENT_TYPE if is_credit_card_hint else DEFAULT_PAYMENT_TYPE,
        )
