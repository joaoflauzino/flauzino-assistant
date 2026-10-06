from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Protocol


class StatementType(str, Enum):
    ACCOUNT = "ACCOUNT"
    CREDIT_CARD = "CREDIT_CARD"


@dataclass
class ParsedTransaction:
    occurred_at: datetime
    posted_at: datetime | None
    raw_title: str
    raw_description: str | None
    raw_row: dict[str, Any]
    amount: Decimal
    direction: str  # "IN" or "OUT"
    balance: Decimal | None = None
    occurrence_index: int = 1
    current_installment: int | None = None
    total_installments: int | None = None
    card_last_digits: str | None = None
    bank_category: str | None = None
    currency: str = "BRL"
    usd_amount: Decimal | None = None
    exchange_rate: Decimal | None = None
    cardholder_name: str | None = None


@dataclass
class StatementMetadata:
    parser_name: str
    bank_name: str
    statement_type: StatementType = StatementType.ACCOUNT
    account_number: str | None = None
    agency: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    card_name: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedStatement:
    metadata: StatementMetadata
    transactions: list[ParsedTransaction]


class StatementParser(Protocol):
    name: str
    statement_type: StatementType

    def can_parse(self, content: bytes, filename: str) -> bool: ...

    def parse(self, content: bytes, filename: str) -> ParsedStatement: ...
