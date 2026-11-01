from enum import Enum, StrEnum


class CardEnum(str, Enum):
    ITAU = "itau"
    PICPAY = "picpay"
    XP = "xp"
    NUBANK = "nubank"
    C6 = "c6"


class NameEnum(str, Enum):
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
