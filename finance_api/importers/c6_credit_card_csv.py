"""Parser for C6 Bank credit card invoice CSV files."""

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from finance_api.core.exceptions import ValidationError
from finance_api.importers.c6_common import (
    ZERO,
    OccurrenceTracker,
    build_csv_reader,
    cell,
    cell_or_none,
    decode_with_fallback,
    find_header_index,
    parse_brl_decimal,
    parse_iso_date,
    parse_statement_datetime,
)
from finance_api.importers.schemas import (
    ParsedStatement,
    ParsedTransaction,
    StatementMetadata,
    StatementType,
)

REQUIRED_COLUMNS = ("Data de Compra", "Final do Cartão", "Valor (em R$)", "Parcela")
DEFAULT_DESCRIPTION = "Compra Cartão C6"
DELIMITER = ";"
DECODE_ERROR = "Não foi possível decodificar o arquivo de fatura C6."
EMPTY_ERROR = "O arquivo de fatura C6 está vazio."
HEADER_ERROR = (
    "Cabeçalho da fatura C6 não encontrado. Verifique se o arquivo possui as colunas esperadas."
)
INSTALLMENT_PATTERN = re.compile(r"^(\d+)/(\d+)$")
FILENAME_DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")
MULTIPLE_SPACES_PATTERN = re.compile(r"\s{2,}")
SINGLE_INSTALLMENT_LABELS = ("única", "unica", "-")


@dataclass
class InvoiceScan:
    """Accumulates the rows, dates and cardholders found in one invoice."""

    transactions: list[ParsedTransaction] = field(default_factory=list)
    dates: list[date] = field(default_factory=list)
    card_names: set[str] = field(default_factory=set)


class C6CreditCardInvoiceCsvParser:
    name: str = "c6_credit_card_csv"
    statement_type: StatementType = StatementType.CREDIT_CARD

    def can_parse(self, content: bytes, filename: str) -> bool:
        head = content[:2048].decode("utf-8-sig", errors="ignore")
        if DELIMITER not in head:
            return False
        return all(column in head for column in REQUIRED_COLUMNS)

    def parse(self, content: bytes, filename: str) -> ParsedStatement:
        text = decode_with_fallback(content, DECODE_ERROR)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            raise ValidationError(EMPTY_ERROR)

        header_index = find_header_index(lines, self._is_header)
        if header_index is None:
            raise ValidationError(HEADER_ERROR)

        scan = self._scan_rows(lines, header_index)
        metadata = self._build_metadata(filename, scan)
        return ParsedStatement(metadata=metadata, transactions=scan.transactions)

    def _is_header(self, line: str) -> bool:
        return "Data de Compra" in line and "Valor (em R$)" in line

    def _scan_rows(self, lines: list[str], header_index: int) -> InvoiceScan:
        reader = build_csv_reader(
            lines,
            header_index,
            delimiter=DELIMITER,
            normalize_fieldnames=True,
        )
        tracker = OccurrenceTracker()
        scan = InvoiceScan()
        for row in reader:
            transaction = self._parse_row(row, tracker, scan)
            if transaction is not None:
                scan.transactions.append(transaction)
        return scan

    def _parse_row(
        self,
        row: dict[str, str | None],
        tracker: OccurrenceTracker,
        scan: InvoiceScan,
    ) -> ParsedTransaction | None:
        purchased_at = parse_statement_datetime(cell(row, "Data de Compra"))
        if purchased_at is None:
            return None

        scan.dates.append(purchased_at.date())
        self._register_cardholder(row, scan)

        direction_amount = self._resolve_amounts(row)
        if direction_amount is None:
            return None
        direction, amount = direction_amount

        card_last_digits = cell_or_none(row, "Final do Cartão")
        category = self._normalize_category(row)
        current_installment, total_installments = self._parse_installments(cell(row, "Parcela"))
        occurrence_index = tracker.next_index(
            (
                purchased_at.date(),
                amount,
                direction,
                self._normalize_title(row),
                current_installment or 1,
            )
        )
        value_usd = parse_brl_decimal(row.get("Valor (em US$)"))
        exchange_rate = parse_brl_decimal(row.get("Cotação (em R$)"))

        return ParsedTransaction(
            occurred_at=purchased_at,
            posted_at=None,
            raw_title=self._normalize_description(row),
            raw_description=self._build_raw_description(row, category, card_last_digits),
            raw_row=dict(row),
            amount=amount,
            direction=direction,
            occurrence_index=occurrence_index,
            current_installment=current_installment,
            total_installments=total_installments,
            card_last_digits=card_last_digits,
            bank_category=category,
            usd_amount=value_usd if value_usd > ZERO else None,
            exchange_rate=exchange_rate if exchange_rate > ZERO else None,
            cardholder_name=cell_or_none(row, "Nome no Cartão"),
        )

    def _register_cardholder(self, row: dict[str, str | None], scan: InvoiceScan) -> None:
        cardholder = cell_or_none(row, "Nome no Cartão")
        if cardholder:
            scan.card_names.add(cardholder)

    def _normalize_category(self, row: dict[str, str | None]) -> str | None:
        category = cell_or_none(row, "Categoria")
        return None if category == "-" else category

    def _normalize_title(self, row: dict[str, str | None]) -> str:
        return self._normalize_description(row).upper().strip()

    def _normalize_description(self, row: dict[str, str | None]) -> str:
        raw_description = cell(row, "Descrição").strip('"').strip()
        description = MULTIPLE_SPACES_PATTERN.sub(" ", raw_description)
        return description or DEFAULT_DESCRIPTION

    def _parse_installments(self, raw_installment: str) -> tuple[int | None, int | None]:
        match = INSTALLMENT_PATTERN.match(raw_installment)
        if not match:
            return None, None
        return int(match.group(1)), int(match.group(2))

    def _resolve_amounts(
        self,
        row: dict[str, str | None],
    ) -> tuple[str, Decimal] | None:
        value_brl = parse_brl_decimal(row.get("Valor (em R$)"))
        value_usd = parse_brl_decimal(row.get("Valor (em US$)"))
        if value_brl == ZERO and value_usd == ZERO:
            return None
        if value_brl < ZERO:
            return "IN", abs(value_brl)
        return "OUT", value_brl

    def _build_raw_description(
        self,
        row: dict[str, str | None],
        category: str | None,
        card_last_digits: str | None,
    ) -> str | None:
        parts = [
            part
            for part in (
                category,
                f"Cartão {card_last_digits}" if card_last_digits else None,
                self._installment_label(cell(row, "Parcela")),
            )
            if part
        ]
        return " | ".join(parts) if parts else None

    def _installment_label(self, raw_installment: str) -> str | None:
        if not raw_installment or raw_installment.lower() in SINGLE_INSTALLMENT_LABELS:
            return None
        return f"Parcela {raw_installment}"

    def _build_metadata(self, filename: str, scan: InvoiceScan) -> StatementMetadata:
        period_start = min(scan.dates) if scan.dates else None
        due_date_token = self._due_date_token(filename)
        period_end = self._merge_due_date(
            max(scan.dates) if scan.dates else None,
            due_date_token,
        )
        extra_info = {"filename": filename}
        if due_date_token:
            extra_info["due_date"] = due_date_token

        card_name = ", ".join(sorted(scan.card_names)) if scan.card_names else None
        return StatementMetadata(
            parser_name=self.name,
            bank_name="c6",
            statement_type=self.statement_type,
            period_start=period_start,
            period_end=period_end,
            card_name=card_name,
            extra=extra_info,
        )

    def _due_date_token(self, filename: str) -> str | None:
        match = FILENAME_DATE_PATTERN.search(filename)
        return match.group(1) if match else None

    def _merge_due_date(self, period_end: date | None, due_date_token: str | None) -> date | None:
        due_date = parse_iso_date(due_date_token)
        if due_date and (period_end is None or due_date > period_end):
            return due_date
        return period_end
