from typing import TypedDict


class AccountCreditCardToolPayload(TypedDict):
    id: str
    key: str
    name: str
    closing_day: int
    due_day: int
    credit_limit: float


class AccountToolPayload(TypedDict):
    id: str
    key: str
    name: str
    bank: str
    owner: str
    type: str
    credit_cards: list[AccountCreditCardToolPayload]


class CreditCardToolPayload(TypedDict):
    id: str
    key: str
    name: str
    account_id: str
    account_name: str | None
    closing_day: int
    due_day: int
    credit_limit: float
