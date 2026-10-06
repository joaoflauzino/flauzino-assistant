import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import io
import re
from zoneinfo import ZoneInfo

from finance_api.core.exceptions import ValidationError
from finance_api.importers.base import (
    ParsedStatement,
    ParsedTransaction,
    StatementMetadata,
    StatementType,
)

SP_TZ = ZoneInfo("America/Sao_Paulo")


class C6CheckingCsvParser:
    name: str = "c6_checking_csv"
    statement_type: StatementType = StatementType.ACCOUNT

    def can_parse(self, content: bytes, filename: str) -> bool:
        try:
            head = content[:1024].decode("utf-8-sig", errors="ignore")
        except Exception:
            return False
        return "EXTRATO DE CONTA CORRENTE C6 BANK" in head or (
            "Data Lançamento" in head and "Saldo do Dia" in head
        )

    def parse(self, content: bytes, filename: str) -> ParsedStatement:
        # Decode content with BOM handling
        text = None
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            raise ValidationError("Não foi possível decodificar o arquivo de extrato.")

        lines = [line.strip() for line in text.splitlines()]

        # Metadata extraction
        agency = None
        account_number = None
        period_start: date | None = None
        period_end: date | None = None

        header_idx = -1
        for idx, line in enumerate(lines):
            if "Agência:" in line and "Conta:" in line:
                m = re.search(r"Agência:\s*([^\s/]+)\s*/\s*Conta:\s*([^\s/]+)", line)
                if m:
                    agency = m.group(1)
                    account_number = m.group(2)
            if "Extrato de" in line and " a " in line:
                m = re.search(r"Extrato de\s*(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})", line)
                if m:
                    try:
                        period_start = datetime.strptime(m.group(1), "%d/%m/%Y").date()
                        period_end = datetime.strptime(m.group(2), "%d/%m/%Y").date()
                    except ValueError:
                        pass
            if line.startswith("Data Lançamento,Data Contábil"):
                header_idx = idx
                break

        if header_idx == -1:
            raise ValidationError(
                "Cabeçalho do extrato C6 não encontrado. Verifique se o arquivo é um CSV de conta corrente C6."
            )

        # Parse CSV rows starting from header_idx
        csv_content = "\n".join(lines[header_idx:])
        reader = csv.DictReader(io.StringIO(csv_content))

        transactions: list[ParsedTransaction] = []
        occurrence_tracker: dict[tuple[date, Decimal, str, str], int] = {}

        for row in reader:
            raw_lanc = (row.get("Data Lançamento") or "").strip()
            if not raw_lanc:
                continue

            try:
                dt_lanc = datetime.strptime(raw_lanc, "%d/%m/%Y").replace(
                    hour=12, minute=0, second=0, tzinfo=SP_TZ
                )
            except ValueError:
                continue

            raw_cont = (row.get("Data Contábil") or "").strip()
            dt_cont = None
            if raw_cont:
                try:
                    dt_cont = datetime.strptime(raw_cont, "%d/%m/%Y").replace(
                        hour=12, minute=0, second=0, tzinfo=SP_TZ
                    )
                except ValueError:
                    pass

            raw_title = (row.get("Título") or "").strip()
            raw_desc = (row.get("Descrição") or "").strip() or None

            def parse_dec(val: str | None) -> Decimal:
                if not val:
                    return Decimal("0.00")
                cleaned = val.strip().replace("R$", "").replace(" ", "").replace(",", ".")
                try:
                    return Decimal(cleaned)
                except InvalidOperation:
                    return Decimal("0.00")

            entrada = parse_dec(row.get("Entrada(R$)"))
            saida = parse_dec(row.get("Saída(R$)"))
            saldo = parse_dec(row.get("Saldo do Dia(R$)"))

            if entrada > Decimal("0.00"):
                direction = "IN"
                amount = entrada
            elif saida > Decimal("0.00"):
                direction = "OUT"
                amount = saida
            else:
                # Transação com valor zero (informativa), ignorar
                continue

            # Track duplicate occurrences on the same day
            norm_title = raw_title.upper().strip()
            dup_key = (dt_lanc.date(), amount, direction, norm_title)
            curr_occ = occurrence_tracker.get(dup_key, 0) + 1
            occurrence_tracker[dup_key] = curr_occ

            tx = ParsedTransaction(
                occurred_at=dt_lanc,
                posted_at=dt_cont,
                raw_title=raw_title,
                raw_description=raw_desc,
                raw_row=dict(row),
                amount=amount,
                direction=direction,
                balance=saldo,
                occurrence_index=curr_occ,
            )
            transactions.append(tx)

        metadata = StatementMetadata(
            parser_name=self.name,
            bank_name="c6",
            statement_type=self.statement_type,
            account_number=account_number,
            agency=agency,
            period_start=period_start,
            period_end=period_end,
            extra={"filename": filename},
        )

        return ParsedStatement(metadata=metadata, transactions=transactions)
