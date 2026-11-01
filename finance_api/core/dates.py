import calendar
from dataclasses import dataclass
from datetime import date, datetime
from typing import Self
from zoneinfo import ZoneInfo

import holidays
from dateutil.relativedelta import relativedelta

from finance_api.core.exceptions import ValidationError


@dataclass(frozen=True)
class DateRange:
    """Immutable Value Object encapsulating a temporal interval and its presentation label."""

    start: date
    end: date
    label: str

    @classmethod
    def from_reference_month(cls, reference_month: str | None = None) -> Self:
        """Parses a reference month string ('YYYY-MM') into a complete civil month date range."""
        if not reference_month:
            now = datetime.now(ZoneInfo("America/Sao_Paulo"))
            reference_month = now.strftime("%Y-%m")

        try:
            parsed_date = datetime.strptime(reference_month, "%Y-%m")
        except ValueError as e:
            raise ValidationError("Formato de mês inválido. Use YYYY-MM.") from e

        year, month = parsed_date.year, parsed_date.month
        start_date = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end_date = date(year, month, last_day)

        return cls(start=start_date, end=end_date, label=reference_month)

    @classmethod
    def from_bounds(
        cls,
        start_date: date | None = None,
        end_date: date | None = None,
        reference_month: str | None = None,
    ) -> Self:
        """Resolves date bounds and label without fragmented procedural if/elif logic."""
        if start_date and end_date:
            label = (
                reference_month
                or f"{start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}"
            )
            return cls(start=start_date, end=end_date, label=label)

        if start_date:
            label = reference_month or f"A partir de {start_date.strftime('%Y-%m-%d')}"
            return cls(start=start_date, end=date(2099, 12, 31), label=label)

        if end_date:
            label = reference_month or f"Até {end_date.strftime('%Y-%m-%d')}"
            return cls(start=date(1970, 1, 1), end=end_date, label=label)

        return cls.from_reference_month(reference_month)


def compute_business_day(reference_month: str, target_day: int) -> date:
    """Calculates the real date for target_day, rolling over weekends and BR holidays."""
    year, month = map(int, reference_month.split("-"))
    _, last_day = calendar.monthrange(year, month)
    day = min(target_day, last_day)

    target_date = date(year, month, day)
    br_holidays = holidays.BR()

    while target_date.weekday() >= 5 or target_date in br_holidays:
        target_date += relativedelta(days=1)

    return target_date


def resolve_due_reference_month(reference_month: str, closing_day: int, due_day: int) -> str:
    """Resolves the reference month for an invoice due date.

    If due_day <= closing_day (e.g. closes on 28th and due on 5th),
    the due date falls into the subsequent month.
    """
    if due_day <= closing_day:
        year, month = map(int, reference_month.split("-"))
        due_date_ref = date(year, month, 1) + relativedelta(months=1)
        return due_date_ref.strftime("%Y-%m")
    return reference_month
