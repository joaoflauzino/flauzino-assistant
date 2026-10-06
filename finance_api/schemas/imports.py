from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PossibleDuplicateInfo(BaseModel):
    type: str  # "spent" or "income"
    id: UUID
    label: str
    amount: float
    date: date


class StagedTransactionResponse(BaseModel):
    id: UUID
    batch_id: UUID
    account_id: UUID | None = None
    credit_card_id: UUID | None = None
    occurred_at: datetime
    posted_at: datetime | None = None
    raw_title: str
    raw_description: str | None = None
    merchant: str
    amount: float
    direction: str  # "IN", "OUT"
    kind: str  # "EXPENSE", "INCOME", "TRANSFER", "INVOICE_PAYMENT", "REFUND"
    payment_type: str
    suggested_category: str | None = None
    suggestion_source: str | None = None  # "RULE", "MEMORY", "LLM"
    confidence: float | None = None
    category: str | None = None
    description: str
    location: str | None = None
    status: str  # "PENDING", "APPROVED", "COMMITTED", "IGNORED", "LINKED"
    current_installment: int | None = None
    total_installments: int | None = None
    card_last_digits: str | None = None
    possible_duplicate: PossibleDuplicateInfo | None = None
    committed_spent_id: UUID | None = None
    committed_income_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class ImportBatchResponse(BaseModel):
    id: UUID
    filename: str
    parser: str
    account_id: UUID | None = None
    account_name: str | None = None
    credit_card_id: UUID | None = None
    credit_card_name: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    total_rows: int
    new_rows: int
    duplicate_rows: int
    possible_duplicates: int
    ai_used: bool
    created_at: datetime
    counts: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class StagedTransactionUpdate(BaseModel):
    category: str | None = None
    kind: str | None = None
    description: str | None = Field(default=None, max_length=50)
    location: str | None = None
    status: str | None = None  # "PENDING", "APPROVED", "IGNORED"
    remember: bool = True


class BulkActionRequest(BaseModel):
    ids: list[UUID]
    action: str  # "approve", "ignore", "reopen", "set_category"
    category: str | None = None
    remember: bool = True


class BulkActionError(BaseModel):
    id: UUID
    error: str


class BulkActionResult(BaseModel):
    updated: int
    skipped: int
    errors: list[BulkActionError] = Field(default_factory=list)


class CommitRequest(BaseModel):
    batch_id: UUID | None = None


class CommitFailure(BaseModel):
    id: UUID
    error: str


class CommitResult(BaseModel):
    committed_spents: int
    committed_incomes: int
    processed_without_record: int
    failed: list[CommitFailure] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    pending: int
    approved: int


class ImportRuleResponse(BaseModel):
    id: UUID
    pattern: str
    match_type: str
    direction: str
    kind: str
    category: str | None
    hits: int
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReclassifyResult(BaseModel):
    total_reclassified: int
    applied_rules: int
    applied_ai: int
