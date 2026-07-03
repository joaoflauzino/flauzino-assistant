from datetime import date
from dateutil.relativedelta import relativedelta
import asyncio


class MockInvService:
    async def get_invoice_dates(self, pm, reference_month):
        if reference_month == "2026-07":
            return date(2026, 6, 3), date(2026, 7, 2)
        elif reference_month == "2026-08":
            return date(2026, 7, 3), date(2026, 8, 2)
        elif reference_month == "2026-06":
            return date(2026, 5, 3), date(2026, 6, 2)


async def test():
    inv_service = MockInvService()
    today = date(2026, 7, 3)
    current_month = today.strftime("%Y-%m")

    start_d, end_d = await inv_service.get_invoice_dates(None, current_month)
    if today > end_d:
        next_month = today + relativedelta(months=1)
        start_d, end_d = await inv_service.get_invoice_dates(None, next_month.strftime("%Y-%m"))
    elif today < start_d:
        prev_month = today - relativedelta(months=1)
        start_d, end_d = await inv_service.get_invoice_dates(None, prev_month.strftime("%Y-%m"))

    print(f"For today {today}, open invoice is {start_d} to {end_d}")

asyncio.run(test())
