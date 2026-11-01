from enum import StrEnum


class CardEnum(StrEnum):
    ITAU = "itau"
    PICPAY = "picpay"
    XP = "xp"
    NUBANK = "nubank"
    C6 = "c6"


class NameEnum(StrEnum):
    JOAO_LUCAS = "joao_lucas"
    LAILLA = "lailla"


class PaymentType(StrEnum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    PIX = "PIX"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"


class TransactionKind(StrEnum):
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"
    TRANSFER = "TRANSFER"
    INVOICE_PAYMENT = "INVOICE_PAYMENT"
    REFUND = "REFUND"


class TransactionDirection(StrEnum):
    IN = "IN"
    OUT = "OUT"


class SuggestionSource(StrEnum):
    RULE = "RULE"
    MEMORY = "MEMORY"
    LLM = "LLM"
    CUSTOM = "CUSTOM"


class BulkActionType(StrEnum):
    APPROVE = "approve"
    IGNORE = "ignore"
    REOPEN = "reopen"
    SET_CATEGORY = "set_category"


class StepOutcomeStatus(StrEnum):
    UPDATED = "updated"
    SKIPPED = "skipped"
    ERROR = "error"


class CommitOutcomeStatus(StrEnum):
    COMMITTED_SPENT = "committed_spent"
    COMMITTED_INCOME = "committed_income"
    PROCESSED_WITHOUT_RECORD = "processed_without_record"
    SKIPPED_NOT_APPROVED = "skipped_not_approved"
    FAILED = "failed"
