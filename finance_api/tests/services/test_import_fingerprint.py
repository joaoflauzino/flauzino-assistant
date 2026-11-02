from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from finance_api.importers.schemas import ParsedTransaction
from finance_api.services.import_fingerprint import ImportFingerprintService

SP_TZ = ZoneInfo("America/Sao_Paulo")


def _tx(**overrides) -> ParsedTransaction:
    base = {
        "occurred_at": datetime(2026, 8, 5, 12, 0, tzinfo=SP_TZ),
        "posted_at": None,
        "raw_title": "Pix enviado para CEMIG",
        "raw_description": "TRANSF ENVIADA PIX",
        "raw_row": {},
        "amount": Decimal("150.00"),
        "direction": "OUT",
        "occurrence_index": 1,
    }
    return ParsedTransaction(**{**base, **overrides})


def test_sha256_is_stable_and_content_sensitive() -> None:
    service = ImportFingerprintService()

    assert service.sha256(b"abc") == service.sha256(b"abc")
    assert service.sha256(b"abc") != service.sha256(b"abd")


def test_build_is_deterministic_for_the_same_row() -> None:
    service = ImportFingerprintService()

    assert service.build("c6_joao", _tx()) == service.build("c6_joao", _tx())


def test_build_changes_with_target_title_installment_and_occurrence() -> None:
    service = ImportFingerprintService()
    baseline = service.build("c6_joao", _tx())

    assert service.build("c6_card", _tx()) != baseline
    assert service.build("c6_joao", _tx(raw_title="Outro")) != baseline
    assert service.build("c6_joao", _tx(occurrence_index=2)) != baseline
    assert (
        service.build(
            "c6_joao",
            _tx(current_installment=2, total_installments=12),
        )
        != baseline
    )


def test_build_map_pairs_every_transaction() -> None:
    service = ImportFingerprintService()
    transactions = [_tx(), _tx(occurrence_index=2)]

    pairs = service.build_map("c6_joao", transactions)

    assert [tx for tx, _ in pairs] == transactions
    assert len({fingerprint for _, fingerprint in pairs}) == 2
