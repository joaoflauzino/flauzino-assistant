"""Chain of Responsibility steps that resolve a payment method key."""

from finance_api.core.logger import get_logger
from finance_api.schemas.payment_resolution import ResolvedPaymentTarget
from finance_api.services.payment_resolution_protocols import PaymentResolutionContext

logger = get_logger(__name__)

VALID_ACCOUNT_PAYMENT_TYPES = frozenset({"PIX", "DEBIT", "CASH", "TRANSFER", "OTHER"})
DEFAULT_ACCOUNT_PAYMENT_TYPE = "DEBIT"


def resolve_account_payment_type(requested_payment_type: str | None) -> str:
    """Returns the requested payment type when valid for accounts, else DEBIT."""
    if requested_payment_type in VALID_ACCOUNT_PAYMENT_TYPES:
        return requested_payment_type
    return DEFAULT_ACCOUNT_PAYMENT_TYPE


class CreditCardPaymentStep:
    """Matches the key against a credit card."""

    async def resolve(self, ctx: PaymentResolutionContext) -> ResolvedPaymentTarget | None:
        if ctx.card_repo is None:
            return None
        card = await ctx.card_repo.get_by_key(ctx.clean_key)
        if card is None:
            return None
        logger.debug(
            f"PaymentResolution: Matched credit card '{ctx.clean_key}' -> card_id={card.id}"
        )
        return ResolvedPaymentTarget(
            account_id=card.account_id,
            credit_card_id=card.id,
            payment_type="CREDIT",
        )


class AccountPaymentStep:
    """Matches the key against a bank account."""

    async def resolve(self, ctx: PaymentResolutionContext) -> ResolvedPaymentTarget | None:
        if ctx.account_repo is None:
            return None
        account = await ctx.account_repo.get_by_key(ctx.clean_key)
        if account is None:
            return None
        logger.debug(
            f"PaymentResolution: Matched account '{ctx.clean_key}' -> account_id={account.id}"
        )
        return ResolvedPaymentTarget(
            account_id=account.id,
            credit_card_id=None,
            payment_type=resolve_account_payment_type(ctx.requested_payment_type),
        )
