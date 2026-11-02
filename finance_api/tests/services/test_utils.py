"""Unit tests for the pure aggregation helpers shared by the finance services."""

from dataclasses import dataclass

from finance_api.services.utils import (
    build_category_balance,
    build_monthly_summary,
    compute_percentage_used,
    compute_savings_rate,
    group_amounts_by_category,
    sum_amounts,
)


@dataclass(frozen=True)
class FakeAmount:
    amount: float
    category: str


def test_sum_amounts_totals_every_item():
    items = [FakeAmount(5000.0, "salario"), FakeAmount(1000.0, "pix")]

    assert sum_amounts(items) == 6000.0
    assert sum_amounts([]) == 0


def test_group_amounts_by_category_accumulates_and_rounds():
    items = [
        FakeAmount(10.005, "mercado"),
        FakeAmount(20.005, "mercado"),
        FakeAmount(5.5, "servicos"),
    ]

    assert group_amounts_by_category(items) == {"mercado": 30.02, "servicos": 5.5}


def test_group_amounts_by_category_keeps_negative_refunds():
    assert group_amounts_by_category([FakeAmount(-50.0, "pix")]) == {"pix": -50.0}


def test_compute_savings_rate_returns_zero_without_income():
    assert compute_savings_rate(net_balance=0.0, total_incomes=0.0) == 0.0


def test_compute_savings_rate_handles_negative_balance():
    assert compute_savings_rate(net_balance=-500.0, total_incomes=1000.0) == -50.0


def test_build_monthly_summary_matches_the_expected_dto():
    summary = build_monthly_summary(
        "2026-08",
        incomes=[FakeAmount(5000.0, "salario"), FakeAmount(1000.0, "pix")],
        spents=[FakeAmount(2000.0, "mercado"), FakeAmount(1000.0, "servicos")],
    )

    assert summary.reference_month == "2026-08"
    assert summary.total_incomes == 6000.0
    assert summary.total_spents == 3000.0
    assert summary.net_balance == 3000.0
    assert summary.is_positive is True
    assert summary.savings_rate == 50.0
    assert summary.incomes_by_category == {"salario": 5000.0, "pix": 1000.0}
    assert summary.spents_by_category == {"mercado": 2000.0, "servicos": 1000.0}


def test_build_monthly_summary_flags_negative_balance():
    summary = build_monthly_summary(
        "2026-08",
        incomes=[],
        spents=[FakeAmount(300.0, "mercado")],
    )

    assert summary.net_balance == -300.0
    assert summary.is_positive is False
    assert summary.savings_rate == 0.0


def test_compute_percentage_used_reports_full_usage_without_a_limit():
    assert compute_percentage_used(spent=250.0, limit_amount=0.0) == 100.0


def test_compute_percentage_used_divides_by_the_limit():
    assert compute_percentage_used(spent=250.0, limit_amount=1000.0) == 25.0


def test_build_category_balance_derives_availability_and_percentage():
    balance = build_category_balance(
        category="mercado",
        display_name="Mercado",
        limit_amount=1000.0,
        spent=250.0,
    )

    assert balance.category == "mercado"
    assert balance.category_display_name == "Mercado"
    assert balance.limit == 1000.0
    assert balance.spent == 250.0
    assert balance.available == 750.0
    assert balance.percentage_used == 25.0


def test_build_category_balance_reports_overspending_as_negative_available():
    balance = build_category_balance(
        category="lazer",
        display_name="Lazer",
        limit_amount=100.0,
        spent=150.0,
    )

    assert balance.available == -50.0
    assert balance.percentage_used == 150.0


def test_build_category_balance_for_a_category_without_limit():
    balance = build_category_balance(
        category="pets",
        display_name="Pets",
        limit_amount=0.0,
        spent=80.0,
    )

    assert balance.limit == 0.0
    assert balance.available == -80.0
    assert balance.percentage_used == 100.0
