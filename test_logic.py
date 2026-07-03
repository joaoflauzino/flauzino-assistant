from datetime import date
import calendar


def compute_real_date(reference_month: str, target_day: int) -> date:
    year, month = map(int, reference_month.split("-"))
    _, last_day = calendar.monthrange(year, month)
    day = min(target_day, last_day)
    return date(year, month, day)


def get_open_invoice_month(closing_day: int, current_date: date) -> str:
    # We want to find the reference_month whose (prev_close < current_date <= current_close)
    # Actually, simpler:
    # If today's day <= closing_day, then the open invoice is this month.
    # If today's day > closing_day, then the open invoice is NEXT month.
    # But wait, what if closing_day is on a weekend and was shifted?
    pass
