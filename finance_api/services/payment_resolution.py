import inspect
from typing import Protocol
from uuid import UUID

from finance_api.core.logger import get_logger
from finance_api.repositories.accounts import AccountRepository, AccountRepositoryProtocol
from finance_api.repositories.credit_cards import (
    CreditCardRepository,
    CreditCardRepositoryProtocol,
)
from finance_api.schemas.payment_resolution import ResolvedPaymentTarget

logger = get_logger(__name__)

VALID_ACCOUNT_PAYMENT_TYPES = ("PIX", "DEBIT", "CASH", "TRANSFER", "OTHER")


class PaymentResolutionServiceProtocol(Protocol):
    async def resolve(
        self,
        payment_method_key: str | None,
        requested_payment_type: str | None = None,
        is_credit_card_hint: bool = False,
    ) -> ResolvedPaymentTarget: ...


class PaymentResolutionService:
    """Domain service responsible for resolving payment relations (account and/or credit card).

    Replaces scattered inline queries and suppressed exception blocks across services.
    """

    def __init__(
        self,
        card_repo: CreditCardRepositoryProtocol | None = None,
        account_repo: AccountRepositoryProtocol | None = None,
        db=None,
    ) -> None:
        self._card_repo = card_repo or (CreditCardRepository(db) if db is not None else None)
        self._account_repo = account_repo or (AccountRepository(db) if db is not None else None)

    async def resolve(
        self,
        payment_method_key: str | None,
        requested_payment_type: str | None = None,
        is_credit_card_hint: bool = False,
    ) -> ResolvedPaymentTarget:
        """Resolves account_id, credit_card_id, and payment_type from a payment method key."""
        if not payment_method_key:
            default_type = requested_payment_type or ("CREDIT" if is_credit_card_hint else "DEBIT")
            return ResolvedPaymentTarget(
                account_id=None,
                credit_card_id=None,
                payment_type=default_type,
            )

        clean_key = payment_method_key.strip().lower()

        # 1. Check if the payment method matches a known credit card
        if self._card_repo is not None:
            try:
                card = await self._card_repo.get_by_key(clean_key)
                if card and hasattr(card, "id") and not inspect.iscoroutine(card.id):
                    card_id = card.id if isinstance(card.id, UUID) else None
                    if card_id is not None:
                        acc_id = getattr(card, "account_id", None)
                        if inspect.iscoroutine(acc_id):
                            acc_id = None
                        logger.debug(f"PaymentResolution: Matched credit card '{clean_key}' -> card_id={card_id}")
                        return ResolvedPaymentTarget(
                            account_id=acc_id,
                            credit_card_id=card_id,
                            payment_type="CREDIT",
                        )
            except Exception as e:
                logger.debug(f"PaymentResolution: Card lookup exception for '{clean_key}': {e}")

        # 2. Check if the payment method matches a known bank account
        if self._account_repo is not None:
            try:
                account = await self._account_repo.get_by_key(clean_key)
                if account and hasattr(account, "id") and not inspect.iscoroutine(account.id):
                    acc_id = account.id if isinstance(account.id, UUID) else None
                    if acc_id is not None:
                        resolved_type = (
                            requested_payment_type
                            if requested_payment_type in VALID_ACCOUNT_PAYMENT_TYPES
                            else "DEBIT"
                        )
                        logger.debug(f"PaymentResolution: Matched account '{clean_key}' -> account_id={acc_id}")
                        return ResolvedPaymentTarget(
                            account_id=acc_id,
                            credit_card_id=None,
                            payment_type=resolved_type,
                        )
            except Exception as e:
                logger.debug(f"PaymentResolution: Account lookup exception for '{clean_key}': {e}")

        # 3. Fallback when neither card nor account explicitly matches
        fallback_type = requested_payment_type or ("CREDIT" if is_credit_card_hint else "DEBIT")
        return ResolvedPaymentTarget(
            account_id=None,
            credit_card_id=None,
            payment_type=fallback_type,
        )
