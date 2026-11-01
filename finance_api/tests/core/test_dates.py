from datetime import date
import pytest

from finance_api.core.dates import (
    DateRange,
    compute_business_day,
    resolve_due_reference_month,
)
from finance_api.core.exceptions import ValidationError


def test_date_range_from_reference_month_valid():
    dr = DateRange.from_reference_month("2026-02")
    assert dr.start == date(2026, 2, 1)
    assert dr.end == date(2026, 2, 28)
    assert dr.label == "2026-02"


def test_date_range_from_reference_month_invalid():
    with pytest.raises(ValidationError, match="Formato de mês inválido"):
        DateRange.from_reference_month("invalid-month")


def test_date_range_from_bounds_both():
    dr = DateRange.from_bounds(date(2026, 1, 1), date(2026, 1, 15))
    assert dr.start == date(2026, 1, 1)
    assert dr.end == date(2026, 1, 15)
    assert dr.label == "2026-01-01 a 2026-01-15"


def test_date_range_from_bounds_start_only():
    dr = DateRange.from_bounds(start_date=date(2026, 5, 10))
    assert dr.start == date(2026, 5, 10)
    assert dr.end == date(2099, 12, 31)
    assert "A partir de 2026-05-10" in dr.label


def test_date_range_from_bounds_end_only():
    dr = DateRange.from_bounds(end_date=date(2026, 5, 10))
    assert dr.start == date(1970, 1, 1)
    assert dr.end == date(2026, 5, 10)
    assert "Até 2026-05-10" in dr.label


def test_compute_business_day_rolls_over_weekend():
    # 2026-10-25 is Sunday -> rolls to Monday 26
    real = compute_business_day("2026-10", 25)
    assert real.weekday() < 5
    assert real == date(2026, 10, 26)


def test_resolve_due_reference_month_subsequent_month():
    # closing 28, due 5 -> next month
    next_month = resolve_due_reference_month("2026-10", closing_day=28, due_day=5)
    assert next_month == "2026-11"


def test_resolve_due_reference_month_same_month():
    # closing 10, due 20 -> same month
    same_month = resolve_due_reference_month("2026-10", closing_day=10, due_day=20)
    assert same_month == "2026-10"
