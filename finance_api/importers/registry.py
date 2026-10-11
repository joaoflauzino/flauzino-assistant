from finance_api.core.exceptions import ValidationError
from finance_api.importers.base import StatementParser
from finance_api.importers.c6_checking_csv import C6CheckingCsvParser
from finance_api.importers.c6_credit_card_csv import C6CreditCardInvoiceCsvParser

_PARSERS: list[StatementParser] = [
    C6CheckingCsvParser(),
    C6CreditCardInvoiceCsvParser(),
]


def detect_parser(content: bytes, filename: str) -> StatementParser:
    for parser in _PARSERS:
        if parser.can_parse(content, filename):
            return parser
    raise ValidationError(
        f"Formato do arquivo '{filename}' não reconhecido. Atualmente suportamos extrato CSV e fatura de cartão de crédito C6."
    )
