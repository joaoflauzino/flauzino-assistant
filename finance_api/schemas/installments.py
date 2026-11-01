from uuid import UUID

from pydantic import BaseModel


class InstallmentSummary(BaseModel):
    installment_id: UUID
    category: str
    item_bought: str
    amount: float
    total_installments: int
    passed_installments: int
