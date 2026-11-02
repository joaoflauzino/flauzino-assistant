from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from finance_api.importers.c6_common import (
    OccurrenceTracker,
    build_csv_reader,
    cell,
    cell_or_none,
    decode_with_fallback,
    find_header_index,
    parse_brl_decimal,
    parse_iso_date,
    parse_statement_date,
    parse_statement_datetime,
)

SP_TZ = ZoneInfo("America/Sao_Paulo")


def test_decode_with_fallback_strips_bom_and_reads_latin1() -> None:
    assert decode_with_fallback(b"\xef\xbb\xbfExtrato", "erro") == "Extrato"
    assert decode_with_fallback("Agência".encode("latin-1"), "erro") == "Agência"


def test_parse_brl_decimal_handles_brazilian_formats() -> None:
    assert parse_brl_decimal("R$ 1.235,25") == Decimal("1235.25")
    assert parse_brl_decimal("235,25") == Decimal("235.25")
    assert parse_brl_decimal('"235,25"') == Decimal("235.25")
    assert parse_brl_decimal("-3610.14") == Decimal("-3610.14")
    assert parse_brl_decimal("") == Decimal("0.00")
    assert parse_brl_decimal(None) == Decimal("0.00")
    assert parse_brl_decimal("invalido") == Decimal("0.00")


def test_parse_statement_datetime_uses_noon_sao_paulo() -> None:
    parsed = parse_statement_datetime("05/08/2026")

    assert parsed == datetime(2026, 8, 5, 12, 0, tzinfo=SP_TZ)
    assert parse_statement_datetime("31/02/2026") is None
    assert parse_statement_datetime("") is None


def test_parse_dates_from_statement_and_iso_formats() -> None:
    assert parse_statement_date("05/08/2026") == date(2026, 8, 5)
    assert parse_iso_date("2026-10-05") == date(2026, 10, 5)
    assert parse_iso_date("not-a-date") is None
    assert parse_iso_date(None) is None


def test_occurrence_tracker_counts_repeated_keys() -> None:
    tracker = OccurrenceTracker()
    key = (date(2026, 9, 9), Decimal("30.00"), "OUT", "GRUPO")

    assert tracker.next_index(key) == 1
    assert tracker.next_index(key) == 2
    assert tracker.next_index(("other",)) == 1


def test_find_header_index_returns_none_when_absent() -> None:
    lines = ["meta", "Data Lançamento,Data Contábil"]

    assert find_header_index(lines, lambda line: line.startswith("Data Lançamento")) == 1
    assert find_header_index(lines, lambda line: line.startswith("Nope")) is None


def test_build_csv_reader_normalizes_fieldnames() -> None:
    lines = [" Data de Compra ; Valor (em R$) ", "26/05/2026;235,25"]
    reader = build_csv_reader(lines, 0, delimiter=";", normalize_fieldnames=True)

    assert reader.fieldnames == ["Data de Compra", "Valor (em R$)"]
    assert next(reader)["Valor (em R$)"] == "235,25"


def test_cell_helpers_trim_and_default() -> None:
    row = {"Título": "  Mercado  ", "Descrição": "   "}

    assert cell(row, "Título") == "Mercado"
    assert cell(row, "Missing") == ""
    assert cell_or_none(row, "Descrição") is None
