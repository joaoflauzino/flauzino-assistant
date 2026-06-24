from pydantic import BaseModel
from uuid import UUID

class InstallmentSummary(BaseModel):
    installment_id: UUID
    category: str
    item_bought: str
    amount: float
    total_installments: int
    passed_installments: int
