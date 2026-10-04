from datetime import date
from decimal import Decimal
import pytest

from finance_api.core.exceptions import ValidationError
from finance_api.importers.c6_checking_csv import C6CheckingCsvParser

SAMPLE_CSV = b"""\xef\xbb\xbfEXTRATO DE CONTA CORRENTE C6 BANK\r
\r
Ag\xc3\xaancia: 1 / Conta: 145118436\r
Extrato gerado em 03/10/2026 - as 13:34:58\r
\r
Extrato de 04/08/2026 a 03/10/2026\r
\r
\r
Data Lan\xc3\xa7amento,Data Cont\xc3\xa1bil,T\xc3\xadtulo,Descri\xc3\xa7\xc3\xa3o,Entrada(R$),Sa\xc3\xadda(R$),Saldo do Dia(R$)\r
05/08/2026,05/08/2026,PGTO FAT CARTAO C6,Fatura de cart\xc3\xa3o,0.00,7452.17,6993.82\r
07/08/2026,07/08/2026,Pix enviado para CEMIG DISTRIBUICAO S.A,TRANSF ENVIADA PIX,0.00,462.73,6351.09\r
10/08/2026,10/08/2026,Pix enviado para Jo\xc3\xa3o Lucas Flauzino Cassiano,TRANSF ENVIADA PIX,0.00,5643.10,0.00\r
20/08/2026,20/08/2026,"CRED ADTO SALARIO ",C6 BANK,7520.00,0.00,7520.00\r
09/09/2026,09/09/2026,GRUPO LUTA PELA VIDA,GRUPO LUTA PELA VIDA,0.00,30.00,943.13\r
09/09/2026,09/09/2026,GRUPO LUTA PELA VIDA,GRUPO LUTA PELA VIDA,0.00,30.00,943.13\r
19/09/2026,21/09/2026,D\xc3\xa9bito de Cart\xc3\xa3o,PAYGO*AUGUSTS BURGE    Uberlandia    BRA. Cart\xc3\xa3o 1633,0.00,79.97,8825.16\r
"""


def test_can_parse_c6_csv():
    parser = C6CheckingCsvParser()
    assert parser.can_parse(SAMPLE_CSV, "extrato.csv") is True
    assert parser.can_parse(b"random content", "file.txt") is False


def test_parse_metadata_and_transactions():
    parser = C6CheckingCsvParser()
    statement = parser.parse(SAMPLE_CSV, "extrato.csv")

    assert statement.metadata.bank_name == "c6"
    assert statement.metadata.account_number == "145118436"
    assert statement.metadata.agency == "1"
    assert statement.metadata.period_start == date(2026, 8, 4)
    assert statement.metadata.period_end == date(2026, 10, 3)

    assert len(statement.transactions) == 7

    # Check first row (PGTO FAT CARTAO C6)
    t0 = statement.transactions[0]
    assert t0.occurred_at.date() == date(2026, 8, 5)
    assert t0.direction == "OUT"
    assert t0.amount == Decimal("7452.17")
    assert t0.occurrence_index == 1

    # Check identical rows on 09/09 (occurrence tracking)
    t_dups = [t for t in statement.transactions if t.raw_title == "GRUPO LUTA PELA VIDA"]
    assert len(t_dups) == 2
    assert t_dups[0].occurrence_index == 1
    assert t_dups[1].occurrence_index == 2

    # Check Entrada row (Salário)
    t_sal = [t for t in statement.transactions if "SALARIO" in t.raw_title][0]
    assert t_sal.direction == "IN"
    assert t_sal.amount == Decimal("7520.00")


def test_parse_invalid_csv_raises_validation_error():
    parser = C6CheckingCsvParser()
    with pytest.raises(ValidationError):
        parser.parse(b"Col1,Col2\nVal1,Val2", "test.csv")
