from typing import TypedDict
from uuid import UUID

from pydantic import BaseModel


class InstallmentSummaryRow(TypedDict):
    """Repository projection used to build an installment summary response."""

    installment_id: UUID
    category: str
    item_bought: str
    amount: float
    total_installments: int
    passed_installments: int


class InstallmentSummary(BaseModel):
    installment_id: UUID
    category: str
    item_bought: str
    amount: float
    total_installments: int
    passed_installments: int
