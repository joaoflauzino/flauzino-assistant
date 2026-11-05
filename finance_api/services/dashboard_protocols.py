"""Structural contracts for the dashboard period strategies."""

from collections.abc import Sequence
from typing import Protocol

from finance_api.models.spents import Spent


class DashboardPeriodStrategy(Protocol):
    """Contract for resolving dashboard spents for a chosen period strategy."""

    async def fetch_spents(
        self,
        reference_month: str,
        skip: int,
        size: int,
    ) -> tuple[Sequence[Spent], int]: ...
