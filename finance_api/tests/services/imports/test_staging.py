from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.importers.schemas import ParsedTransaction, ResolvedImportTarget
from finance_api.schemas.classification import ClassificationResult
from finance_api.services.imports.staging import (
    StagingBuilder,
    resolve_salary_competence_date,
)

SP_TZ = ZoneInfo("America/Sao_Paulo")


def _tx(**overrides) -> ParsedTransaction:
    base = {
        "occurred_at": datetime(2026, 10, 1, 9, 0, tzinfo=SP_TZ),
        "posted_at": datetime(2026, 10, 1, 9, 0, tzinfo=SP_TZ),
        "raw_title": "CRED SALARIO MENSAL",
        "raw_description": "C6 BANK",
        "raw_row": {"linha": "1"},
        "amount": Decimal("5000.00"),
        "direction": "IN",
        "current_installment": 1,
        "total_installments": 1,
        "card_last_digits": "1141",
    }
    return ParsedTransaction(**{**base, **overrides})


@pytest.fixture
def target() -> ResolvedImportTarget:
    return ResolvedImportTarget(
        account_id=uuid4(),
        credit_card_id=None,
        target_key="c6_joao",
        target_name="C6 (João Lucas)",
    )


@pytest.mark.asyncio
async def test_build_maps_classification_and_counts_duplicates(target) -> None:
    classification_service = MagicMock()
    classification_service.classify_transaction = AsyncMock(
        return_value=ClassificationResult(
            merchant="C6 BANK",
            kind="INCOME",
            payment_type="OTHER",
            suggested_category="salario",
            suggestion_source="RULE",
            confidence=Decimal("0.900"),
            description="Salário",
            location="Brasil",
        )
    )
    duplicate_id = uuid4()
    detector = MagicMock()
    detector.detect = AsyncMock(return_value=(None, duplicate_id))
    builder = StagingBuilder(
        tx_repo=MagicMock(),
        classification_service=classification_service,
        duplicate_detectors={"INCOME": detector},
    )

    staged, duplicates = await builder.build(
        batch_id=uuid4(),
        target=target,
        new_pairs=[(_tx(), "fp-1")],
        is_credit_card=False,
    )

    assert duplicates == 1
    assert len(staged) == 1
    row = staged[0]
    assert row.fingerprint == "fp-1"
    assert row.kind == "INCOME"
    assert row.category == "salario"
    assert row.possible_duplicate_of_income_id == duplicate_id
    assert row.current_installment == 1
    assert row.card_last_digits == "1141"
    assert row.status == "PENDING"
    classification_service.classify_transaction.assert_awaited_once()
    assert classification_service.classify_transaction.call_args.kwargs["bank_category"] is None


@pytest.mark.asyncio
async def test_build_without_detector_for_kind_keeps_rows_clean(target) -> None:
    classification_service = MagicMock()
    classification_service.classify_transaction = AsyncMock(
        return_value=ClassificationResult(
            merchant="CEMIG",
            kind="EXPENSE",
            payment_type="DEBIT",
            suggested_category=None,
            suggestion_source=None,
            confidence=None,
            description="Conta de luz",
        )
    )
    builder = StagingBuilder(
        tx_repo=MagicMock(),
        classification_service=classification_service,
        duplicate_detectors={},
    )

    staged, duplicates = await builder.build(
        batch_id=uuid4(),
        target=target,
        new_pairs=[(_tx(), "fp-1")],
        is_credit_card=False,
    )

    assert duplicates == 0
    assert staged[0].possible_duplicate_of_spent_id is None
    assert staged[0].possible_duplicate_of_income_id is None


def test_salary_competence_date_shifts_to_the_previous_month_last_day() -> None:
    """Salaries credited in the first week belong to the previous competence month."""
    result = resolve_salary_competence_date(
        kind="INCOME",
        occurred_at=datetime(2026, 10, 1, 9, 0, tzinfo=SP_TZ),
        raw_title="CRED SALARIO MENSAL",
        raw_description="C6 BANK",
    )

    assert result == date(2026, 9, 30)


def test_salary_competence_date_keeps_the_occurrence_date_after_the_first_week() -> None:
    result = resolve_salary_competence_date(
        kind="INCOME",
        occurred_at=datetime(2026, 10, 20, 9, 0, tzinfo=SP_TZ),
        raw_title="CRED SALARIO MENSAL",
        raw_description="C6 BANK",
    )

    assert result == date(2026, 10, 20)


def test_salary_competence_date_keeps_the_occurrence_date_for_non_salary_income() -> None:
    result = resolve_salary_competence_date(
        kind="INCOME",
        occurred_at=datetime(2026, 10, 2, 9, 0, tzinfo=SP_TZ),
        raw_title="Pix recebido de Carlos",
        raw_description="PIX RECEBIDO",
    )

    assert result == date(2026, 10, 2)


def test_competence_date_is_none_outside_income_kind() -> None:
    result = resolve_salary_competence_date(
        kind="EXPENSE",
        occurred_at=datetime(2026, 10, 1, 9, 0, tzinfo=SP_TZ),
        raw_title="CRED SALARIO MENSAL",
        raw_description=None,
    )

    assert result is None
