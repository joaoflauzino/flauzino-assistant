"""Parser for C6 Bank checking account CSV statements."""

import re
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
    parse_statement_date,
    parse_statement_datetime,
)
from finance_api.importers.schemas import (
    ParsedStatement,
    ParsedTransaction,
    StatementMetadata,
    StatementType,
)

TITLE_MARKER = "EXTRATO DE CONTA CORRENTE C6 BANK"
HEADER_PREFIX = "Data Lançamento,Data Contábil"
HEADER_ERROR = (
    "Cabeçalho do extrato C6 não encontrado. Verifique se o arquivo é um CSV de conta corrente C6."
)
DECODE_ERROR = "Não foi possível decodificar o arquivo de extrato."
AGENCY_PATTERN = re.compile(r"Agência:\s*([^\s/]+)\s*/\s*Conta:\s*([^\s/]+)")
PERIOD_PATTERN = re.compile(r"Extrato de\s*(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})")


class C6CheckingCsvParser:
    name: str = "c6_checking_csv"
    statement_type: StatementType = StatementType.ACCOUNT

    def can_parse(self, content: bytes, filename: str) -> bool:
        head = content[:1024].decode("utf-8-sig", errors="ignore")
        return TITLE_MARKER in head or ("Data Lançamento" in head and "Saldo do Dia" in head)

    def parse(self, content: bytes, filename: str) -> ParsedStatement:
        text = decode_with_fallback(content, DECODE_ERROR)
        lines = [line.strip() for line in text.splitlines()]

        header_index = find_header_index(lines, self._is_header)
        if header_index is None:
            raise ValidationError(HEADER_ERROR)

        metadata = self._build_metadata(lines[:header_index], filename)
        transactions = self._read_transactions(lines, header_index)
        return ParsedStatement(metadata=metadata, transactions=transactions)

    def _is_header(self, line: str) -> bool:
        return line.startswith(HEADER_PREFIX)

    def _build_metadata(self, header_lines: list[str], filename: str) -> StatementMetadata:
        agency, account_number = self._extract_agency_account(header_lines)
        period_start, period_end = self._extract_period(header_lines)
        return StatementMetadata(
            parser_name=self.name,
            bank_name="c6",
            statement_type=self.statement_type,
            account_number=account_number,
            agency=agency,
            period_start=period_start,
            period_end=period_end,
            extra={"filename": filename},
        )

    def _extract_agency_account(
        self,
        header_lines: list[str],
    ) -> tuple[str | None, str | None]:
        for line in header_lines:
            match = AGENCY_PATTERN.search(line)
            if match:
                return match.group(1), match.group(2)
        return None, None

    def _extract_period(self, header_lines: list[str]) -> tuple[date | None, date | None]:
        for line in header_lines:
            match = PERIOD_PATTERN.search(line)
            if not match:
                continue
            start = parse_statement_date(match.group(1))
            end = parse_statement_date(match.group(2))
            if start and end:
                return start, end
        return None, None

    def _read_transactions(
        self,
        lines: list[str],
        header_index: int,
    ) -> list[ParsedTransaction]:
        reader = build_csv_reader(lines, header_index)
        tracker = OccurrenceTracker()
        transactions: list[ParsedTransaction] = []
        for row in reader:
            transaction = self._parse_row(row, tracker)
            if transaction is not None:
                transactions.append(transaction)
        return transactions

    def _parse_row(
        self,
        row: dict[str, str | None],
        tracker: OccurrenceTracker,
    ) -> ParsedTransaction | None:
        occurred_at = parse_statement_datetime(cell(row, "Data Lançamento"))
        if occurred_at is None:
            return None

        direction_amount = self._resolve_direction(row)
        if direction_amount is None:
            return None
        direction, amount = direction_amount

        title = cell(row, "Título")
        occurrence_index = tracker.next_index(
            (occurred_at.date(), amount, direction, title.upper())
        )
        return ParsedTransaction(
            occurred_at=occurred_at,
            posted_at=parse_statement_datetime(cell(row, "Data Contábil")),
            raw_title=title,
            raw_description=cell_or_none(row, "Descrição"),
            raw_row=dict(row),
            amount=amount,
            direction=direction,
            balance=parse_brl_decimal(row.get("Saldo do Dia(R$)")),
            occurrence_index=occurrence_index,
        )

    def _resolve_direction(
        self,
        row: dict[str, str | None],
    ) -> tuple[str, Decimal] | None:
        entrada = parse_brl_decimal(row.get("Entrada(R$)"))
        saida = parse_brl_decimal(row.get("Saída(R$)"))
        if entrada > ZERO:
            return "IN", entrada
        if saida > ZERO:
            return "OUT", saida
        return None
