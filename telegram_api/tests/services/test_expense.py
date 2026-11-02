"""Unit tests for the expense persistence service."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from telegram_api.services.expense import (
    ExpenseData,
    build_spent_data,
    build_subscription_data,
    persist_expense,
    resolve_saver,
    save_continuous_subscription,
    save_installment,
    save_single_purchase,
)

EXPENSE: ExpenseData = {
    "category": "mercado",
    "amount": 80.0,
    "item_bought": "carne",
    "payment_method": "c6_joao",
    "location": "BH",
}

save_spent_path = "telegram_api.services.expense.save_spent"
save_subscription_path = "telegram_api.services.expense.save_subscription"


def test_build_spent_data_maps_the_expense_fields():
    assert build_spent_data(EXPENSE) == {
        "category": "mercado",
        "amount": 80.0,
        "item_bought": "carne",
        "payment_method": "c6_joao",
        "location": "BH",
    }


def test_build_spent_data_defaults_the_location():
    assert build_spent_data({**EXPENSE, "location": None})["location"] is None
    assert (
        build_spent_data({k: v for k, v in EXPENSE.items() if k != "location"})["location"] == "N/A"
    )


def test_build_spent_data_includes_the_chosen_datetime_as_isoformat():
    created_at = datetime(2026, 10, 1, 12, 30)

    payload = build_spent_data({**EXPENSE, "created_at": created_at})

    assert payload["created_at"] == created_at.isoformat()


def test_build_subscription_data_uses_the_item_as_name():
    payload = build_subscription_data({**EXPENSE, "created_at": datetime(2026, 10, 1)})

    assert payload["name"] == "carne"
    assert payload["category"] == "mercado"
    assert "location" not in payload
    assert "created_at" in payload


@pytest.mark.asyncio
async def test_save_single_purchase_posts_a_spent():
    with patch(save_spent_path, new=AsyncMock()) as save_spent:
        await save_single_purchase(EXPENSE)

    save_spent.assert_awaited_once_with(build_spent_data(EXPENSE))


@pytest.mark.asyncio
async def test_save_installment_records_the_installments():
    expense = {**EXPENSE, "current_installment": 4, "total_installments": 12}

    with patch(save_spent_path, new=AsyncMock()) as save_spent:
        await save_installment(expense)

    payload = save_spent.await_args.args[0]
    assert payload["is_installment"] is True
    assert payload["current_installment"] == 4
    assert payload["total_installments"] == 12


@pytest.mark.asyncio
async def test_save_continuous_subscription_posts_a_subscription():
    with patch(save_subscription_path, new=AsyncMock()) as save_subscription:
        await save_continuous_subscription(EXPENSE)

    save_subscription.assert_awaited_once_with(build_subscription_data(EXPENSE))


def test_resolve_saver_falls_back_to_single_purchase():
    assert resolve_saver({}) is save_single_purchase
    assert resolve_saver({"purchase_type": "desconhecido"}) is save_single_purchase
    assert resolve_saver({"purchase_type": "parcelada"}) is save_installment


@pytest.mark.asyncio
async def test_persist_expense_dispatches_by_purchase_type():
    expense = {**EXPENSE, "purchase_type": "assinatura"}

    with patch(save_subscription_path, new=AsyncMock()) as save_subscription:
        await persist_expense(expense)

    save_subscription.assert_awaited_once()
