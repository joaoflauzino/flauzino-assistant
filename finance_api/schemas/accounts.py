from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from finance_api.schemas.credit_cards import CreditCardResponse


class AccountBase(BaseModel):
    key: str = Field(..., max_length=50, description="Unique key for the account")
    name: str = Field(..., max_length=100, description="Name of the account")
    bank: str = Field(default="outro", max_length=50, description="Bank or institution")
    owner: str = Field(default="joao", max_length=50, description="Account owner")
    type: str = Field(
        default="CHECKING",
        max_length=30,
        description="Account type: CHECKING, SAVINGS, WALLET, INVESTMENT",
    )


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    key: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, max_length=100)
    bank: str | None = Field(default=None, max_length=50)
    owner: str | None = Field(default=None, max_length=50)
    type: str | None = Field(default=None, max_length=30)


class AccountResponse(AccountBase):
    id: UUID
    created_at: datetime
    credit_cards: list[CreditCardResponse] = []

    model_config = ConfigDict(from_attributes=True)
