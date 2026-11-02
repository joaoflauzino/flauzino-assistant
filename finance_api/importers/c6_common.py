"""Shared primitives for the C6 CSV importers."""

import csv
import io
from collections.abc import Callable, Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from finance_api.core.exceptions import ValidationError

SP_TZ = ZoneInfo("America/Sao_Paulo")
ZERO = Decimal("0.00")
DATE_FORMAT = "%d/%m/%Y"
ENCODINGS = ("utf-8-sig", "utf-8", "latin-1")


def decode_with_fallback(content: bytes, error_message: str) -> str:
    """Decodes ``content`` trying the encodings used by C6 exports."""
    for encoding in ENCODINGS:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValidationError(error_message)


def parse_brl_decimal(value: str | None) -> Decimal:
    """Parses Brazilian money strings such as ``R$ 1.235,25``."""
    if not value:
        return ZERO
    cleaned = (
        value.strip()
        .replace("R$", "")
        .replace("US$", "")
        .replace("$", "")
        .replace(" ", "")
        .replace('"', "")
    )
    try:
        return Decimal(normalize_separators(cleaned))
    except InvalidOperation:
        return ZERO


def normalize_separators(cleaned: str) -> str:
    if "," in cleaned and "." not in cleaned:
        return cleaned.replace(",", ".")
    if "," in cleaned and "." in cleaned:
        return cleaned.replace(".", "").replace(",", ".")
    return cleaned


def parse_statement_datetime(value: str | None) -> datetime | None:
    """Parses a ``dd/mm/YYYY`` cell into a noon timestamp in São Paulo time."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT).replace(
            hour=12,
            minute=0,
            second=0,
            tzinfo=SP_TZ,
        )
    except ValueError:
        return None


def parse_statement_date(value: str | None) -> date | None:
    parsed = parse_statement_datetime(value)
    return parsed.date() if parsed else None


def parse_iso_date(value: str | None) -> date | None:
    """Parses an ISO ``YYYY-MM-DD`` date, returning ``None`` when invalid."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def cell(row: Mapping[str, str | None], name: str) -> str:
    """Returns a trimmed CSV cell, defaulting to an empty string."""
    return (row.get(name) or "").strip()


def cell_or_none(row: Mapping[str, str | None], name: str) -> str | None:
    value = cell(row, name)
    return value or None


def find_header_index(lines: Iterable[str], predicate: Callable[[str], bool]) -> int | None:
    """Returns the index of the first line matching ``predicate``, if any."""
    for index, line in enumerate(lines):
        if predicate(line):
            return index
    return None


def build_csv_reader(
    lines: list[str],
    header_index: int,
    delimiter: str = ",",
    normalize_fieldnames: bool = False,
) -> csv.DictReader:
    """Builds a ``DictReader`` starting at the header line."""
    reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])), delimiter=delimiter)
    if normalize_fieldnames and reader.fieldnames:
        reader.fieldnames = [field.strip() for field in reader.fieldnames if field]
    return reader


class OccurrenceTracker:
    """Counts repeated rows sharing the same natural key."""

    def __init__(self) -> None:
        self._counts: dict[tuple[Any, ...], int] = {}

    def next_index(self, key: tuple[Any, ...]) -> int:
        count = self._counts.get(key, 0) + 1
        self._counts[key] = count
        return count
