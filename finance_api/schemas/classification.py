from dataclasses import dataclass
from decimal import Decimal

from finance_api.schemas.enums import (
    PaymentType,
    SuggestionSource,
    TransactionDirection,
    TransactionKind,
)


@dataclass(frozen=True)
class RawTransactionText:
    """Raw text payload extracted from bank statement transaction."""

    title: str
    description: str
    norm_title: str
    direction: TransactionDirection | str


@dataclass(frozen=True)
class ExtractedMerchantInfo:
    """Structured merchant and location details parsed by extractor pipeline."""

    merchant: str
    location: str | None
    short_description: str


@dataclass(frozen=True)
class ClassificationContext:
    """Immutable context passed through the classification Chain of Responsibility."""

    raw_title: str
    raw_description: str | None
    norm_title: str
    norm_desc: str
    norm_combined: str
    direction: str
    amount: Decimal
    merchant: str
    location: str | None
    description: str
    default_kind: TransactionKind | str
    default_payment_type: PaymentType | str
    bank_category: str | None = None
    is_credit_card: bool = False


@dataclass
class ClassificationResult:
    """Final output of the transaction classification pipeline."""

    merchant: str
    kind: TransactionKind | str
    payment_type: PaymentType | str
    suggested_category: str | None
    suggestion_source: SuggestionSource | str | None
    confidence: Decimal | None
    description: str
    location: str | None = None


# Mapeamento heurístico de categorias fornecidas por bancos (ex: C6) para categorias do sistema
BANK_CATEGORY_MAP: dict[str, tuple[str, Decimal]] = {
    "RESTAURANTE / LANCHONETE / BAR": ("comer_fora", Decimal("0.950")),
    "SUPERMERCADOS / MERCEARIA / PADARIAS / LOJAS DE CONVENIENCIA": ("mercado", Decimal("0.950")),
    "ASSISTENCIA MEDICA E ODONTOLOGICA": ("saude", Decimal("0.950")),
    "TRANSPORTE": ("transporte", Decimal("0.950")),
    "RELACIONADOS A AUTOMOTIVO": ("transporte", Decimal("0.900")),
    "TV POR ASSINATURA / SERVICOS DE RADIO": ("servicos", Decimal("0.950")),
    "SERVICOS DE TELECOMUNICACOES": ("servicos", Decimal("0.950")),
    "VESTUARIO / ROUPAS": ("vestuario", Decimal("0.950")),
    "ALUGUEL": ("moradia", Decimal("0.900")),
    "ESPECIALIDADE VAREJO": ("compras", Decimal("0.850")),
    "DEPARTAMENTO / DESCONTO": ("compras", Decimal("0.850")),
    "T&E": ("viagem", Decimal("0.900")),
    "MARKETING DIRETO": ("outros", Decimal("0.800")),
    "SERVICOS PESSOAIS": ("servicos", Decimal("0.850")),
}
