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


class C6CreditCardInvoiceCsvParser:
    name: str = "c6_credit_card_csv"
    statement_type: StatementType = StatementType.CREDIT_CARD

    def can_parse(self, content: bytes, filename: str) -> bool:
        try:
            head = content[:2048].decode("utf-8-sig", errors="ignore")
        except Exception:
            return False

        # Verifica se o arquivo tem delimitador ';' e colunas típicas da fatura de cartão C6
        if ";" not in head:
            return False

        required_cols = [
            "Data de Compra",
            "Final do Cartão",
            "Valor (em R$)",
            "Parcela",
        ]
        return all(col in head for col in required_cols)

    def parse(self, content: bytes, filename: str) -> ParsedStatement:
        # Decode content com fallback de encodings
        text = None
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            raise ValidationError("Não foi possível decodificar o arquivo de fatura C6.")

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            raise ValidationError("O arquivo de fatura C6 está vazio.")

        # Localiza a linha do cabeçalho
        header_idx = -1
        for idx, line in enumerate(lines):
            if "Data de Compra" in line and "Valor (em R$)" in line:
                header_idx = idx
                break

        if header_idx == -1:
            raise ValidationError(
                "Cabeçalho da fatura C6 não encontrado. Verifique se o arquivo possui as colunas esperadas."
            )

        csv_content = "\n".join(lines[header_idx:])
        reader = csv.DictReader(io.StringIO(csv_content), delimiter=";")

        # Normaliza nomes de colunas do reader (remove espaços ao redor)
        if reader.fieldnames:
            reader.fieldnames = [col.strip() for col in reader.fieldnames if col]

        transactions: list[ParsedTransaction] = []
        occurrence_tracker: dict[tuple[date, Decimal, str, str, int], int] = {}
        all_dates: list[date] = []
        card_names: set[str] = set()

        def parse_dec(val: str | None) -> Decimal:
            if not val:
                return Decimal("0.00")
            cleaned = (
                val.strip()
                .replace("R$", "")
                .replace("US$", "")
                .replace("$", "")
                .replace(" ", "")
                .replace('"', "")
            )
            # Trata vírgula como separador decimal caso presente (ex: 235,25)
            if "," in cleaned and "." not in cleaned:
                cleaned = cleaned.replace(",", ".")
            elif "," in cleaned and "." in cleaned:
                # Caso venha no padrão brasileiro com milhar: 1.235,25
                cleaned = cleaned.replace(".", "").replace(",", ".")
            try:
                return Decimal(cleaned)
            except InvalidOperation:
                return Decimal("0.00")

        for row in reader:
            raw_date = (row.get("Data de Compra") or "").strip()
            if not raw_date:
                continue

            try:
                dt_compra = datetime.strptime(raw_date, "%d/%m/%Y").replace(
                    hour=12, minute=0, second=0, tzinfo=SP_TZ
                )
            except ValueError:
                continue

            all_dates.append(dt_compra.date())

            nome_cartao = (row.get("Nome no Cartão") or "").strip() or None
            if nome_cartao:
                card_names.add(nome_cartao)

            final_cartao = (row.get("Final do Cartão") or "").strip() or None
            categoria = (row.get("Categoria") or "").strip() or None
            if categoria == "-":
                categoria = None

            raw_desc = (row.get("Descrição") or "").strip().strip('"').strip()
            # Limpeza de múltiplos espaços internos comuns na fatura do C6
            desc = re.sub(r"\s{2,}", " ", raw_desc)
            if not desc:
                desc = "Compra Cartão C6"

            raw_parcela = (row.get("Parcela") or "").strip()
            current_installment: int | None = None
            total_installments: int | None = None

            m_parc = re.match(r"^(\d+)/(\d+)$", raw_parcela)
            if m_parc:
                current_installment = int(m_parc.group(1))
                total_installments = int(m_parc.group(2))

            val_brl = parse_dec(row.get("Valor (em R$)"))
            val_usd = parse_dec(row.get("Valor (em US$)"))
            val_cotacao = parse_dec(row.get("Cotação (em R$)"))

            if val_brl == Decimal("0.00") and val_usd == Decimal("0.00"):
                continue

            if val_brl < Decimal("0.00"):
                amount = abs(val_brl)
                direction = "IN"
            else:
                amount = val_brl
                direction = "OUT"

            # Identificação de duplicatas repetidas no mesmo dia e mesma parcela
            norm_title = desc.upper().strip()
            installment_key = current_installment or 1
            dup_key = (dt_compra.date(), amount, direction, norm_title, installment_key)
            curr_occ = occurrence_tracker.get(dup_key, 0) + 1
            occurrence_tracker[dup_key] = curr_occ

            raw_desc_parts = []
            if categoria:
                raw_desc_parts.append(categoria)
            if final_cartao:
                raw_desc_parts.append(f"Cartão {final_cartao}")
            if raw_parcela and raw_parcela.lower() not in ("única", "unica", "-"):
                raw_desc_parts.append(f"Parcela {raw_parcela}")
            raw_description = " | ".join(raw_desc_parts) if raw_desc_parts else None

            tx = ParsedTransaction(
                occurred_at=dt_compra,
                posted_at=None,
                raw_title=desc,
                raw_description=raw_description,
                raw_row=dict(row),
                amount=amount,
                direction=direction,
                occurrence_index=curr_occ,
                current_installment=current_installment,
                total_installments=total_installments,
                card_last_digits=final_cartao,
                bank_category=categoria,
                usd_amount=val_usd if val_usd > Decimal("0.00") else None,
                exchange_rate=val_cotacao if val_cotacao > Decimal("0.00") else None,
                cardholder_name=nome_cartao,
            )
            transactions.append(tx)

        # Extrai data de vencimento / período
        period_start = min(all_dates) if all_dates else None
        period_end = max(all_dates) if all_dates else None

        # Se o nome do arquivo contiver data (ex: Fatura_2026-10-05.csv), usa como referência
        m_filename_date = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
        extra_info: dict[str, str] = {"filename": filename}
        if m_filename_date:
            extra_info["due_date"] = m_filename_date.group(1)
            try:
                fn_due = datetime.strptime(m_filename_date.group(1), "%Y-%m-%d").date()
                if period_end is None or fn_due > period_end:
                    period_end = fn_due
            except ValueError:
                pass

        card_name_meta = ", ".join(sorted(card_names)) if card_names else None

        metadata = StatementMetadata(
            parser_name=self.name,
            bank_name="c6",
            statement_type=self.statement_type,
            period_start=period_start,
            period_end=period_end,
            card_name=card_name_meta,
            extra=extra_info,
        )

        return ParsedStatement(metadata=metadata, transactions=transactions)
