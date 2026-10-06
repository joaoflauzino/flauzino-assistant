from datetime import date
from decimal import Decimal
import pytest

from finance_api.core.exceptions import ValidationError
from finance_api.importers.base import StatementType
from finance_api.importers.c6_credit_card_csv import C6CreditCardInvoiceCsvParser

SAMPLE_CARD_CSV = b"""Data de Compra;Nome no Cart\xc3\xa3o;Final do Cart\xc3\xa3o;Categoria;Descri\xc3\xa7\xc3\xa3o;Parcela;Valor (em US$);Cota\xc3\xa7\xc3\xa3o (em R$);Valor (em R$)
26/05/2026;JOAO L F CASSIANO;1141;Empresa para empresa;DELL;4/12;0;0;235.25
11/08/2026;JOAO L F CASSIANO;1141;T&E;HOT BEACH SUITES HOSP;2/10;0;0;233.00
28/08/2026;JOAO L F CASSIANO;1141;Restaurante / Lanchonete / Bar;IFD*MARA SELVA NADLER;\xc3\x9anica;0;0;96.69
05/09/2026;JOAO L F CASSIANO;1633;-;"Inclusao de Pagamento    ";\xc3\x9anica;0;0;-3610.14
23/09/2026;JOAO L F CASSIANO;1633;-;Anuidade Diferenciada;11/12;0;0;98.00
23/09/2026;JOAO L F CASSIANO;1633;-;Estorno Tarifa;\xc3\x9anica;0;0;-98.00
26/09/2026;JOAO L F CASSIANO;1633;El\xc3\xa9trico;OPENAI                 SA;\xc3\x9anica;5.00;5.45;27.25
"""


def test_can_parse_c6_credit_card_csv():
    parser = C6CreditCardInvoiceCsvParser()
    assert parser.can_parse(SAMPLE_CARD_CSV, "Fatura_2026-10-05.csv") is True
    assert parser.can_parse(b"random,content,without,semicolons", "file.csv") is False
    assert parser.statement_type == StatementType.CREDIT_CARD


def test_parse_c6_credit_card_transactions():
    parser = C6CreditCardInvoiceCsvParser()
    statement = parser.parse(SAMPLE_CARD_CSV, "Fatura_2026-10-05.csv")

    assert statement.metadata.bank_name == "c6"
    assert statement.metadata.statement_type == StatementType.CREDIT_CARD
    assert statement.metadata.extra.get("due_date") == "2026-10-05"
    assert statement.metadata.period_end == date(2026, 10, 5)

    txs = statement.transactions
    assert len(txs) == 7

    # 1. Parcela DELL 4/12
    t_dell = txs[0]
    assert t_dell.raw_title == "DELL"
    assert t_dell.occurred_at.date() == date(2026, 5, 26)
    assert t_dell.amount == Decimal("235.25")
    assert t_dell.direction == "OUT"
    assert t_dell.current_installment == 4
    assert t_dell.total_installments == 12
    assert t_dell.card_last_digits == "1141"
    assert t_dell.bank_category == "Empresa para empresa"
    assert t_dell.cardholder_name == "JOAO L F CASSIANO"

    # 2. Compra à vista restaurante
    t_rest = txs[2]
    assert t_rest.raw_title == "IFD*MARA SELVA NADLER"
    assert t_rest.amount == Decimal("96.69")
    assert t_rest.direction == "OUT"
    assert t_rest.current_installment is None
    assert t_rest.total_installments is None
    assert t_rest.bank_category == "Restaurante / Lanchonete / Bar"

    # 3. Inclusão de Pagamento (negativo)
    t_pgto = txs[3]
    assert t_pgto.raw_title == "Inclusao de Pagamento"
    assert t_pgto.amount == Decimal("3610.14")
    assert t_pgto.direction == "IN"
    assert t_pgto.bank_category is None

    # 4. Estorno Tarifa (negativo)
    t_est = txs[5]
    assert t_est.raw_title == "Estorno Tarifa"
    assert t_est.amount == Decimal("98.00")
    assert t_est.direction == "IN"

    # 5. Compra Internacional (USD + Cotação)
    t_intl = txs[6]
    assert t_intl.raw_title == "OPENAI SA"
    assert t_intl.amount == Decimal("27.25")
    assert t_intl.usd_amount == Decimal("5.00")
    assert t_intl.exchange_rate == Decimal("5.45")
    assert t_intl.card_last_digits == "1633"


def test_parse_empty_card_csv_raises_error():
    parser = C6CreditCardInvoiceCsvParser()
    with pytest.raises(ValidationError):
        parser.parse(b"", "empty.csv")
