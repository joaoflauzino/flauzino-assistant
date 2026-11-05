"""Preparation steps shared by the update() family of finance services.

Each step validates one concern and enriches the update payload in place, so the
services only orchestrate: prepare -> existence guard -> repository update.
"""

from collections.abc import Sequence

from finance_api.core.exceptions import ValidationError
from finance_api.models.payment_methods import PaymentMethod
from finance_api.schemas.incomes import IncomeUpdate
from finance_api.schemas.payment_resolution import ResolvedPaymentTarget
from finance_api.schemas.spents import SpentUpdate
from finance_api.schemas.subscriptions import SubscriptionUpdate
from finance_api.services.lookup_protocols import (
    CategoryLookupProtocol,
    IncomeCategoryLookupProtocol,
    PaymentMethodLookupProtocol,
)
from finance_api.services.payment_resolution_protocols import PaymentResolutionServiceProtocol
from finance_api.services.update_preparation_protocols import (
    PaymentTargetPayload,
    UpdatePreparationStep,
)


class UpdateDataPreparer[T]:
    """Runs the preparation steps of an update payload in order."""

    def __init__(self, steps: Sequence[UpdatePreparationStep[T]]) -> None:
        self._steps = steps

    async def prepare(self, data: T) -> None:
        for step in self._steps:
            await step.prepare(data)


def apply_payment_target(data: PaymentTargetPayload, target: ResolvedPaymentTarget) -> None:
    """Applies the resolved account, credit card and payment type to the payload."""
    if target.credit_card_id:
        data.credit_card_id = target.credit_card_id
    if target.account_id:
        data.account_id = target.account_id
    data.payment_type = target.payment_type


class ExpenseCategoryStep:
    """Validates and normalizes the category key of expense-based payloads."""

    MESSAGE = "Categoria '{key}' não existe. Por favor, crie-a primeiro."

    def __init__(self, category_repo: CategoryLookupProtocol) -> None:
        self._category_repo = category_repo

    async def prepare(self, data: SpentUpdate | SubscriptionUpdate) -> None:
        if not data.category:
            return

        category = await self._category_repo.get_by_key(data.category)
        if category is None:
            raise ValidationError(self.MESSAGE.format(key=data.category))

        data.category = category.key


class IncomeCategoryStep:
    """Validates the category key of income payloads."""

    MESSAGE = "Categoria de receita '{key}' não existe. Por favor, crie-a primeiro."

    def __init__(self, category_repo: IncomeCategoryLookupProtocol) -> None:
        self._category_repo = category_repo

    async def prepare(self, data: IncomeUpdate) -> None:
        if not data.category:
            return

        if await self._category_repo.get_by_key(data.category):
            return

        raise ValidationError(self.MESSAGE.format(key=data.category))


class SpentPaymentStep:
    """Validates the payment method and resolves its account/credit card relations."""

    MESSAGE = "Método de pagamento '{key}' não existe. Por favor, crie-o primeiro."

    def __init__(
        self,
        pm_repo: PaymentMethodLookupProtocol,
        resolver: PaymentResolutionServiceProtocol,
    ) -> None:
        self._pm_repo = pm_repo
        self._resolver = resolver

    async def prepare(self, data: SpentUpdate) -> None:
        if not data.payment_method:
            return

        payment_method = await self._require_payment_method(data.payment_method)
        data.payment_method = payment_method.key
        target = await self._resolver.resolve(
            payment_method.key,
            requested_payment_type=data.payment_type,
            is_credit_card_hint=payment_method.is_credit_card,
        )
        apply_payment_target(data, target)

    async def _require_payment_method(self, key: str) -> PaymentMethod:
        payment_method = await self._pm_repo.get_by_key(key)
        if payment_method is None:
            raise ValidationError(self.MESSAGE.format(key=key))

        return payment_method


class IncomePaymentStep:
    """Validates the payment method and fills the account when it was not informed."""

    MESSAGE = "Método de pagamento '{key}' não existe."

    def __init__(
        self,
        pm_repo: PaymentMethodLookupProtocol,
        resolver: PaymentResolutionServiceProtocol,
    ) -> None:
        self._pm_repo = pm_repo
        self._resolver = resolver

    async def prepare(self, data: IncomeUpdate) -> None:
        if not data.payment_method:
            return

        payment_method = await self._require_payment_method(data.payment_method)
        data.payment_method = payment_method.key
        if data.account_id:
            return

        target = await self._resolver.resolve(payment_method.key)
        if target.account_id:
            data.account_id = target.account_id

    async def _require_payment_method(self, key: str) -> PaymentMethod:
        payment_method = await self._pm_repo.get_by_key(key)
        if payment_method is None:
            raise ValidationError(self.MESSAGE.format(key=key))

        return payment_method


class SubscriptionPaymentStep:
    """Resolves the account/credit card relations of a subscription payment method."""

    def __init__(self, resolver: PaymentResolutionServiceProtocol) -> None:
        self._resolver = resolver

    async def prepare(self, data: SubscriptionUpdate) -> None:
        if not data.payment_method:
            return

        target = await self._resolver.resolve(
            data.payment_method,
            requested_payment_type=data.payment_type,
        )
        apply_payment_target(data, target)
