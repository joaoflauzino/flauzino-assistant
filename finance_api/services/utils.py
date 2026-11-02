"""Pure aggregation helpers shared by the finance services."""

from collections.abc import Iterable

from finance_api.schemas.incomes import MonthlyBalanceSummary
from finance_api.schemas.limits import CategoryBalance
from finance_api.services.protocols import CategorizedAmountProtocol


def sum_amounts(items: Iterable[CategorizedAmountProtocol]) -> float:
    """Sums the amount of every item."""
    return sum(item.amount for item in items)


def group_amounts_by_category(items: Iterable[CategorizedAmountProtocol]) -> dict[str, float]:
    """Sums amounts per category, rounding each partial total to cents."""
    totals: dict[str, float] = {}
    for item in items:
        totals[item.category] = round(totals.get(item.category, 0.0) + item.amount, 2)
    return totals


def compute_savings_rate(net_balance: float, total_incomes: float) -> float:
    """Percentage of the income that was not spent, zero when there is no income."""
    if total_incomes <= 0:
        return 0.0
    return round((net_balance / total_incomes) * 100, 2)


def compute_percentage_used(spent: float, limit_amount: float) -> float:
    """Percentage of the limit already spent; a category without a limit is reported as 100%."""
    if limit_amount <= 0:
        return 100.0
    return (spent / limit_amount) * 100


def build_category_balance(
    category: str,
    display_name: str,
    limit_amount: float,
    spent: float,
) -> CategoryBalance:
    """Builds a category balance entry, deriving availability and percentage used."""
    return CategoryBalance(
        category=category,
        category_display_name=display_name,
        limit=limit_amount,
        spent=spent,
        available=limit_amount - spent,
        percentage_used=compute_percentage_used(spent, limit_amount),
    )


def build_monthly_summary(
    reference_month: str,
    incomes: Iterable[CategorizedAmountProtocol],
    spents: Iterable[CategorizedAmountProtocol],
) -> MonthlyBalanceSummary:
    """Assembles the monthly balance DTO from the period's incomes and spents."""
    income_items = list(incomes)
    spent_items = list(spents)
    total_incomes = sum_amounts(income_items)
    total_spents = sum_amounts(spent_items)
    net_balance = round(total_incomes - total_spents, 2)

    return MonthlyBalanceSummary(
        reference_month=reference_month,
        total_incomes=round(total_incomes, 2),
        total_spents=round(total_spents, 2),
        net_balance=net_balance,
        is_positive=net_balance >= 0,
        savings_rate=compute_savings_rate(net_balance, total_incomes),
        incomes_by_category=group_amounts_by_category(income_items),
        spents_by_category=group_amounts_by_category(spent_items),
    )
