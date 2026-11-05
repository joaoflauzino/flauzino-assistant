"""Protocols and structural contracts for agent_api services."""

from typing import Protocol

from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.finance import BalancePayload
from agent_api.schemas.income import IncomeDetails
from agent_api.schemas.limit import LimitDetails
from agent_api.schemas.spending import SpendingDetails


class FinanceServiceProtocol(Protocol):
    """Structural protocol defining the contract for finance service interactions."""

    async def get_categories(self, use_cache: bool = True) -> list[str]: ...

    async def get_income_categories(self, use_cache: bool = True) -> list[str]: ...

    async def get_accounts(self, use_cache: bool = True) -> list[str]: ...

    async def get_credit_cards(self, use_cache: bool = True) -> list[str]: ...

    async def get_payment_methods(self, use_cache: bool = True) -> list[str]: ...

    async def get_balances(
        self,
        categories: list[str] | None = None,
        reference_month: str | None = None,
    ) -> list[BalancePayload]: ...

    async def get_monthly_summary(self, reference_month: str | None = None) -> dict: ...

    async def register(self, response: AssistantResponse) -> dict | None: ...

    async def save_spent(self, details: SpendingDetails) -> dict: ...

    async def save_income(self, details: IncomeDetails) -> dict: ...

    async def save_limit(self, details: LimitDetails) -> dict: ...


class GraphServiceProtocol(Protocol):
    """Structural protocol defining the contract for chart generation."""

    async def generate_chart(
        self,
        chart_type: str,
        balances: list[BalancePayload],
        mode: str = "saldo",
        title: str | None = None,
    ) -> str: ...
