from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
import pytest

from finance_api.core.dependencies import get_category_rule_repository, get_import_service
from finance_api.main import app
from finance_api.models.category_rules import CategoryRule
from finance_api.repositories.category_rules import CategoryRuleRepository
from finance_api.schemas.imports import (
    CommitResult,
    StagedTransactionResponse,
    SummaryResponse,
)
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.services.imports import ImportService


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


def test_list_rules_router(client):
    mock_repo = MagicMock(spec=CategoryRuleRepository)
    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    mock_repo.list_all = AsyncMock(
        return_value=[
            CategoryRule(
                id=uuid4(),
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

    app.dependency_overrides[get_category_rule_repository] = lambda: mock_repo
    try:
        res = client.get("/import-rules/")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["pattern"] == "CEMIG"
        assert data[0]["category"] == "moradia"
    finally:
        app.dependency_overrides.clear()
