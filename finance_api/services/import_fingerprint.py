"""Deterministic fingerprinting helpers for bank statement imports."""

import hashlib

from finance_api.importers.schemas import ParsedTransaction


class ImportFingerprintService:
    """Builds stable content hashes used to detect duplicate imports and rows."""

    def sha256(self, content: bytes) -> str:
        """Returns the hexadecimal SHA-256 digest of the uploaded file."""
        return hashlib.sha256(content).hexdigest()

    def build(self, target_key: str, tx: ParsedTransaction) -> str:
        """Builds the row fingerprint for a parsed transaction."""
        date_str = tx.occurred_at.date().isoformat()
        amount_str = f"{tx.amount:.2f}"
        installment_str = (
            f"{tx.current_installment}/{tx.total_installments}" if tx.current_installment else "1"
        )
        raw = (
            f"{target_key}|{date_str}|{amount_str}|{tx.direction}|"
            f"{tx.raw_title.upper().strip()}|{installment_str}|{tx.occurrence_index}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def build_map(
        self,
        target_key: str,
        transactions: list[ParsedTransaction],
    ) -> list[tuple[ParsedTransaction, str]]:
        """Pairs every parsed transaction with its fingerprint."""
        return [(tx, self.build(target_key, tx)) for tx in transactions]
