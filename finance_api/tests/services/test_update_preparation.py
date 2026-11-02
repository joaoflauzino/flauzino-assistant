from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import ValidationError
from finance_api.models.categories import Category
from finance_api.models.income_categories import IncomeCategory
from finance_api.models.payment_methods import PaymentMethod
from finance_api.schemas.incomes import IncomeUpdate
from finance_api.schemas.payment_resolution import ResolvedPaymentTarget
from finance_api.schemas.spents import SpentUpdate
from finance_api.schemas.subscriptions import SubscriptionUpdate
from finance_api.services.update_preparation import (
    ExpenseCategoryStep,
    IncomeCategoryStep,
    IncomePaymentStep,
    SpentPaymentStep,
    SubscriptionPaymentStep,
    UpdateDataPreparer,
    apply_payment_target,
)

pytestmark = pytest.mark.asyncio


class RecordingStep:
    def __init__(self, name: str, calls: list[str], error: Exception | None = None) -> None:
        self._name = name
        self._calls = calls
        self._error = error

    async def prepare(self, data: object) -> None:
        self._calls.append(self._name)
        if self._error is not None:
            raise self._error


def make_payment_method(key: str = "itau_joao", is_credit_card: bool = True) -> PaymentMethod:
    return PaymentMethod(id=uuid4(), key=key, display_name="Itaú", is_credit_card=is_credit_card)


async def test_preparer_runs_steps_in_order():
    calls: list[str] = []
    preparer = UpdateDataPreparer((RecordingStep("first", calls), RecordingStep("second", calls)))

    await preparer.prepare({"value": 1})

    assert calls == ["first", "second"]


async def test_preparer_stops_on_first_error():
    calls: list[str] = []
    preparer = UpdateDataPreparer(
        (
            RecordingStep("first", calls),
            RecordingStep("second", calls, error=ValidationError("boom")),
            RecordingStep("third", calls),
        )
    )

    with pytest.raises(ValidationError):
        await preparer.prepare({"value": 1})

    assert calls == ["first", "second"]


async def test_expense_category_step_normalizes_key():
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = Category(
        id=uuid4(), key="mercado", display_name="Mercado"
    )
    step = ExpenseCategoryStep(category_repo)
    data = SpentUpdate(category="mercado")

    await step.prepare(data)

    category_repo.get_by_key.assert_awaited_once_with("mercado")
    assert data.category == "mercado"


async def test_expense_category_step_ignores_missing_category():
    category_repo = AsyncMock()
    step = ExpenseCategoryStep(category_repo)

    await step.prepare(SpentUpdate(amount=10.0))

    category_repo.get_by_key.assert_not_awaited()


async def test_expense_category_step_raises_for_unknown_category():
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = None
    step = ExpenseCategoryStep(category_repo)

    with pytest.raises(ValidationError, match="Categoria 'inexistente' não existe"):
        await step.prepare(SpentUpdate(category="inexistente"))


async def test_income_category_step_raises_with_income_message():
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = None
    step = IncomeCategoryStep(category_repo)

    with pytest.raises(ValidationError, match="Categoria de receita 'bonus' não existe"):
        await step.prepare(IncomeUpdate(category="bonus"))


async def test_income_category_step_accepts_existing_category():
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = IncomeCategory(
        id=uuid4(), key="salario", display_name="Salário"
    )
    step = IncomeCategoryStep(category_repo)
    data = IncomeUpdate(category="salario")

    await step.prepare(data)

    assert data.category == "salario"


async def test_spent_payment_step_applies_full_target():
    pm_repo = AsyncMock()
    pm_repo.get_by_key.return_value = make_payment_method(is_credit_card=True)
    resolver = AsyncMock()
    account_id = uuid4()
    card_id = uuid4()
    resolver.resolve.return_value = ResolvedPaymentTarget(
        account_id=account_id, credit_card_id=card_id, payment_type="CREDIT"
    )
    step = SpentPaymentStep(pm_repo, resolver)
    data = SpentUpdate(payment_method="itau_joao", payment_type="CREDIT")

    await step.prepare(data)

    resolver.resolve.assert_awaited_once_with(
        "itau_joao", requested_payment_type="CREDIT", is_credit_card_hint=True
    )
    assert data.credit_card_id == card_id
    assert data.account_id == account_id
    assert data.payment_type == "CREDIT"


async def test_spent_payment_step_raises_for_unknown_payment_method():
    pm_repo = AsyncMock()
    pm_repo.get_by_key.return_value = None
    step = SpentPaymentStep(pm_repo, AsyncMock())

    with pytest.raises(ValidationError, match="Método de pagamento 'fantasma' não existe"):
        await step.prepare(SpentUpdate(payment_method="fantasma"))


async def test_income_payment_step_skips_resolution_when_account_informed():
    pm_repo = AsyncMock()
    pm_repo.get_by_key.return_value = make_payment_method(is_credit_card=False)
    resolver = AsyncMock()
    step = IncomePaymentStep(pm_repo, resolver)
    account_id = uuid4()
    data = IncomeUpdate(payment_method="itau_joao", account_id=account_id)

    await step.prepare(data)

    resolver.resolve.assert_not_awaited()
    assert data.payment_method == "itau_joao"
    assert data.account_id == account_id


async def test_income_payment_step_fills_account_from_resolution():
    pm_repo = AsyncMock()
    pm_repo.get_by_key.return_value = make_payment_method(is_credit_card=False)
    resolver = AsyncMock()
    account_id = uuid4()
    resolver.resolve.return_value = ResolvedPaymentTarget(
        account_id=account_id, credit_card_id=None, payment_type="DEBIT"
    )
    step = IncomePaymentStep(pm_repo, resolver)
    data = IncomeUpdate(payment_method="itau_joao")

    await step.prepare(data)

    resolver.resolve.assert_awaited_once_with("itau_joao")
    assert data.account_id == account_id


async def test_subscription_payment_step_applies_target():
    resolver = AsyncMock()
    card_id = uuid4()
    resolver.resolve.return_value = ResolvedPaymentTarget(
        account_id=None, credit_card_id=card_id, payment_type="CREDIT"
    )
    step = SubscriptionPaymentStep(resolver)
    data = SubscriptionUpdate(payment_method="itau_card")

    await step.prepare(data)

    resolver.resolve.assert_awaited_once_with("itau_card", requested_payment_type=None)
    assert data.credit_card_id == card_id
    assert data.payment_type == "CREDIT"


async def test_apply_payment_target_keeps_existing_relations_when_target_is_empty():
    data = SpentUpdate(payment_method="pix")

    apply_payment_target(
        data,
        ResolvedPaymentTarget(account_id=None, credit_card_id=None, payment_type="PIX"),
    )

    assert data.credit_card_id is None
    assert data.account_id is None
    assert data.payment_type == "PIX"
