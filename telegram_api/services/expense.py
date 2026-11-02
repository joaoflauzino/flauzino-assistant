"""Expense persistence: builds the finance payloads and runs the selected saver."""

from collections.abc import Awaitable, Callable
from typing import Any

from telegram_api.core.finance_client import save_spent, save_subscription

type ExpenseData = dict[str, Any]
type PurchaseSaver = Callable[[ExpenseData], Awaitable[None]]


def with_created_at(data: ExpenseData, expense: ExpenseData) -> ExpenseData:
    """Copies the chosen purchase datetime (when present) into the payload."""
    if "created_at" in expense:
        data["created_at"] = expense["created_at"].isoformat()
    return data


def build_spent_data(expense: ExpenseData) -> ExpenseData:
    """Builds the ``POST /spents`` payload from the collected expense data."""
    spent_data: ExpenseData = {
        "category": expense.get("category"),
        "amount": expense.get("amount"),
        "item_bought": expense.get("item_bought"),
        "payment_method": expense.get("payment_method"),
        "location": expense.get("location", "N/A"),
    }
    return with_created_at(spent_data, expense)


def build_subscription_data(expense: ExpenseData) -> ExpenseData:
    """Builds the ``POST /subscriptions`` payload from the collected expense data."""
    subscription_data: ExpenseData = {
        "name": expense.get("item_bought"),
        "category": expense.get("category"),
        "amount": expense.get("amount"),
        "payment_method": expense.get("payment_method"),
    }
    return with_created_at(subscription_data, expense)


async def save_single_purchase(expense: ExpenseData) -> None:
    """Persists a one-off purchase as a spent."""
    await save_spent(build_spent_data(expense))


async def save_installment(expense: ExpenseData) -> None:
    """Persists an installment purchase, recording the current and total installments."""
    spent_data = build_spent_data(expense)
    spent_data["is_installment"] = True
    spent_data["current_installment"] = expense.get("current_installment", 1)
    spent_data["total_installments"] = expense.get("total_installments", 1)
    await save_spent(spent_data)


async def save_continuous_subscription(expense: ExpenseData) -> None:
    """Persists a continuous subscription."""
    await save_subscription(build_subscription_data(expense))


PURCHASE_SAVERS: dict[str, PurchaseSaver] = {
    "a_vista": save_single_purchase,
    "parcelada": save_installment,
    "assinatura": save_continuous_subscription,
}


def resolve_saver(expense: ExpenseData) -> PurchaseSaver:
    """Selects the saver for the expense purchase type, defaulting to a one-off purchase."""
    return PURCHASE_SAVERS.get(expense.get("purchase_type", "a_vista"), save_single_purchase)


async def persist_expense(expense: ExpenseData) -> None:
    """Persists the expense through the saver selected by its purchase type."""
    await resolve_saver(expense)(expense)
