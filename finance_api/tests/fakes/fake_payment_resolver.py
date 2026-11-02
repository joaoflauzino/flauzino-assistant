from collections.abc import Mapping

from finance_api.schemas.payment_resolution import ResolvedPaymentTarget


class FakePaymentResolver:
    """Deterministic in-memory implementation of the payment resolution contract."""

    def __init__(self, targets: Mapping[str, ResolvedPaymentTarget] | None = None) -> None:
        self._targets = {key.lower(): target for key, target in (targets or {}).items()}

    async def resolve(
        self,
        payment_method_key: str | None,
        requested_payment_type: str | None = None,
        is_credit_card_hint: bool = False,
    ) -> ResolvedPaymentTarget:
        if payment_method_key:
            target = self._targets.get(payment_method_key.strip().lower())
            if target is not None:
                return target

        if requested_payment_type:
            payment_type = requested_payment_type
        else:
            payment_type = "CREDIT" if is_credit_card_hint else "DEBIT"

        return ResolvedPaymentTarget(
            account_id=None,
            credit_card_id=None,
            payment_type=payment_type,
        )
