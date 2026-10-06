from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncomeBase(BaseModel):
    description: str = Field(..., min_length=1, description="Descrição da receita")
    amount: float = Field(..., gt=0, description="Valor da receita em reais")
    category: str = Field(
        ..., min_length=1, max_length=50, description="Chave da categoria de receita"
    )
    payment_method: str | None = Field(
        default=None, max_length=50, description="Chave da conta/método de recebimento"
    )
    account_id: UUID | None = Field(default=None, description="ID da conta bancária de recebimento")
    received_at: datetime | None = Field(
        default=None, description="Data/hora em que a receita foi recebida"
    )
    competence_date: date | None = Field(default=None, description="Data de competência da receita")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str | None) -> str | None:
        return v.lower().strip() if v else None


class IncomeCreate(IncomeBase):
    pass


class IncomeUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1)
    amount: float | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    payment_method: str | None = Field(default=None, max_length=50)
    account_id: UUID | None = None
    received_at: datetime | None = None
    competence_date: date | None = None

    @field_validator("category")
    @classmethod
    def validate_category_update(cls, v: str | None) -> str | None:
        return v.lower().strip() if v else None

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method_update(cls, v: str | None) -> str | None:
        return v.lower().strip() if v else None


class IncomeResponse(BaseModel):
    id: UUID
    description: str
    amount: float
    category: str
    payment_method: str | None = None
    account_id: UUID | None = None
    received_at: datetime
    competence_date: date | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonthlyBalanceSummary(BaseModel):
    reference_month: str
    total_incomes: float
    total_spents: float
    net_balance: float
    is_positive: bool
    savings_rate: float
    incomes_by_category: dict[str, float]
    spents_by_category: dict[str, float]
