from finance_api.core.exceptions import ValidationError
from finance_api.importers.base import StatementParser
from finance_api.importers.c6_checking_csv import C6CheckingCsvParser

_PARSERS: list[StatementParser] = [
    C6CheckingCsvParser(),
]


def detect_parser(content: bytes, filename: str) -> StatementParser:
    for parser in _PARSERS:
        if parser.can_parse(content, filename):
            return parser
    raise ValidationError(
        f"Formato do arquivo '{filename}' não reconhecido. Atualmente suportamos extrato CSV de conta corrente C6."
    )
