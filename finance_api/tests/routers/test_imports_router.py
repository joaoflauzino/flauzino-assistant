from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from finance_api.core.dependencies import (
    get_account_repository,
    get_account_service,
    get_category_repository,
    get_category_rule_repository,
    get_classification_service,
    get_credit_card_repository,
    get_credit_card_service,
    get_import_batch_repository,
    get_import_service,
    get_income_category_repository,
    get_income_repository,
    get_invoice_repository,
    get_invoice_service,
    get_parser_factory,
    get_payment_method_repository,
    get_spending_limit_repository,
    get_spending_limit_service,
    get_spent_repository,
    get_staged_transaction_repository,
    get_target_resolvers,
)
from finance_api.core.exceptions import EntityNotFoundError
from finance_api.main import app
from finance_api.models.category_rules import CategoryRule
from finance_api.schemas.imports import (
    CommitResult,
    ImportBatchResponse,
    StagedTransactionResponse,
    SummaryResponse,
)
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.services.classification import ClassificationService
from finance_api.services.imports.facade import ImportService


@pytest.fixture
def client():
    return TestClient(app)


def test_get_summary_router(client):
    mock_service = MagicMock(spec=ImportService)
    mock_service.get_summary = AsyncMock(return_value=SummaryResponse(pending=5, approved=2))

    app.dependency_overrides[get_import_service] = lambda: mock_service
    try:
        res = client.get("/imports/summary")
        assert res.status_code == 200
        data = res.json()
        assert data["pending"] == 5
        assert data["approved"] == 2
    finally:
        app.dependency_overrides.clear()


def test_upload_statement_router_empty_and_success(client):
    mock_service = MagicMock(spec=ImportService)
    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    mock_service.create_batch_from_upload = AsyncMock(
        return_value=ImportBatchResponse(
            id=uuid4(),
            filename="extrato.csv",
            file_sha256="sha256",
            parser="c6_checking",
            total_rows=1,
            new_rows=1,
            duplicate_rows=0,
            possible_duplicates=0,
            ai_used=False,
            created_at=now,
        )
    )

    app.dependency_overrides[get_import_service] = lambda: mock_service
    try:
        # Empty file -> ValidationError (400/422)
        res_empty = client.post(
            "/imports/",
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        assert res_empty.status_code in (400, 422)
        assert "Arquivo vazio" in res_empty.text

        # Non-empty file -> 201 Created
        res_ok = client.post(
            "/imports/",
            files={"file": ("extrato.csv", b"col1,col2\n1,2", "text/csv")},
        )
        assert res_ok.status_code == 201
        assert res_ok.json()["filename"] == "extrato.csv"
    finally:
        app.dependency_overrides.clear()


def test_list_batches_router(client):
    mock_service = MagicMock(spec=ImportService)
    mock_service.list_batches = AsyncMock(return_value=[])

    app.dependency_overrides[get_import_service] = lambda: mock_service
    try:
        res = client.get("/imports/")
        assert res.status_code == 200
        assert res.json() == []
    finally:
        app.dependency_overrides.clear()


def test_list_transactions_router(client):
    mock_service = MagicMock(spec=ImportService)
    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    tx_resp = StagedTransactionResponse(
        id=uuid4(),
        batch_id=uuid4(),
        occurred_at=now,
        raw_title="Padaria",
        merchant="Padaria",
        amount=15.0,
        direction="OUT",
        kind="EXPENSE",
        payment_type="DEBIT",
        description="Padaria",
        location="Brasil",
        status="PENDING",
    )
    mock_service.list_transactions = AsyncMock(
        return_value=PaginatedResponse.create([tx_resp], 1, 1, 50)
    )

    app.dependency_overrides[get_import_service] = lambda: mock_service
    try:
        res = client.get("/imports/transactions?status=PENDING")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["raw_title"] == "Padaria"
    finally:
        app.dependency_overrides.clear()


def test_commit_router(client):
    mock_service = MagicMock(spec=ImportService)
    mock_service.commit_approved = AsyncMock(
        return_value=CommitResult(
            committed_spents=3,
            committed_incomes=1,
            processed_without_record=2,
            failed=[],
        )
    )

    app.dependency_overrides[get_import_service] = lambda: mock_service
    try:
        res = client.post("/imports/commit", json={})
        assert res.status_code == 200
        data = res.json()
        assert data["committed_spents"] == 3
        assert data["committed_incomes"] == 1
        assert data["processed_without_record"] == 2
    finally:
        app.dependency_overrides.clear()


def test_list_and_delete_rules_router(client):
    mock_clf_service = MagicMock(spec=ClassificationService)
    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    rule_id = uuid4()
    mock_clf_service.list_rules = AsyncMock(
        return_value=[
            CategoryRule(
                id=rule_id,
                pattern="CEMIG",
                match_type="CONTAINS",
                direction="OUT",
                kind="EXPENSE",
                category="moradia",
                hits=5,
                source="SEED",
                created_at=now,
                updated_at=now,
            )
        ]
    )
    mock_clf_service.delete_rule = AsyncMock(return_value=None)

    app.dependency_overrides[get_classification_service] = lambda: mock_clf_service
    try:
        res = client.get("/import-rules/")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["pattern"] == "CEMIG"
        assert data[0]["category"] == "moradia"

        del_res = client.delete(f"/import-rules/{rule_id}")
        assert del_res.status_code == 204
        mock_clf_service.delete_rule.assert_awaited_once_with(rule_id)

        mock_clf_service.delete_rule = AsyncMock(
            side_effect=EntityNotFoundError(f"Regra com ID {rule_id} não encontrada.")
        )
        not_found_res = client.delete(f"/import-rules/{rule_id}")
        assert not_found_res.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_dependency_providers_wiring():
    mock_db = MagicMock()
    acc_repo = get_account_repository(mock_db)
    cc_repo = get_credit_card_repository(mock_db)
    cat_repo = get_category_repository(mock_db)
    inc_cat_repo = get_income_category_repository(mock_db)
    pm_repo = get_payment_method_repository(mock_db)
    inv_repo = get_invoice_repository(mock_db)
    spent_repo = get_spent_repository(mock_db)
    inc_repo = get_income_repository(mock_db)
    limit_repo = get_spending_limit_repository(mock_db)
    rule_repo = get_category_rule_repository(mock_db)
    batch_repo = get_import_batch_repository(mock_db)
    tx_repo = get_staged_transaction_repository(mock_db)
    parser_factory = get_parser_factory()
    target_resolvers = get_target_resolvers(acc_repo, cc_repo)

    assert acc_repo is not None
    assert spent_repo is not None
    assert inc_repo is not None
    assert limit_repo is not None
    assert parser_factory is not None
    assert target_resolvers is not None

    inv_svc = get_invoice_service(inv_repo, pm_repo)
    limit_svc = get_spending_limit_service(mock_db)
    acc_svc = get_account_service(mock_db)
    cc_svc = get_credit_card_service(mock_db)
    clf_svc = get_classification_service(rule_repo)
    imp_svc = get_import_service(
        batch_repo=batch_repo,
        tx_repo=tx_repo,
        rule_repo=rule_repo,
        clf_service=clf_svc,
        acc_repo=acc_repo,
        cc_repo=cc_repo,
        cat_repo=cat_repo,
        inc_cat_repo=inc_cat_repo,
        spent_svc=MagicMock(),
        inc_svc=MagicMock(),
        parser_factory=parser_factory,
        target_resolvers=target_resolvers,
    )

    assert inv_svc is not None
    assert limit_svc is not None
    assert acc_svc is not None
    assert cc_svc is not None
    assert imp_svc.batch_repo == batch_repo
