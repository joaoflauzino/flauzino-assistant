from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol


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


@dataclass
class StatementMetadata:
    parser_name: str
    bank_name: str
    account_number: str | None = None
    agency: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedStatement:
    metadata: StatementMetadata
    transactions: list[ParsedTransaction]


class StatementParser(Protocol):
    name: str

    def can_parse(self, content: bytes, filename: str) -> bool: ...

    def parse(self, content: bytes, filename: str) -> ParsedStatement: ...
