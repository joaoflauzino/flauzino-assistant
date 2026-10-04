from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import pytest

from agent_api.dependencies import get_classify_service
from agent_api.main import app
from agent_api.schemas.classify import ClassifyBatchResponse, ClassifySuggestion
from agent_api.services.classify import ClassifyService


@pytest.fixture
def client():
    return TestClient(app)


def test_classify_router_success(client):
    mock_service = MagicMock(spec=ClassifyService)
    mock_service.classify_transactions = AsyncMock(
        return_value=ClassifyBatchResponse(
            suggestions=[ClassifySuggestion(id="tx-1", category="alimentacao", confidence=0.85)]
        )
    )

    app.dependency_overrides[get_classify_service] = lambda: mock_service

    try:
        response = client.post(
            "/classify/transactions",
            json={
                "transactions": [
                    {
                        "id": "tx-1",
                        "merchant": "PADARIA CENTRAL",
                        "raw_title": "Débito",
                        "direction": "OUT",
                        "amount": 10.0,
                    }
                ],
                "expense_categories": [{"key": "alimentacao", "display_name": "Alimentação"}],
                "income_categories": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["category"] == "alimentacao"
    finally:
        app.dependency_overrides.clear()
