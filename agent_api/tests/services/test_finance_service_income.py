from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.income import IncomeDetails
from agent_api.services.finance import FinanceService


@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def finance_service(mock_client):
    return FinanceService(client=mock_client)


@pytest.mark.asyncio
async def test_get_income_categories_success(finance_service, mock_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [{"key": "salario"}, {"key": "pix"}],
        "total": 2,
    }
    mock_client.get.return_value = mock_response

    cats = await finance_service.get_income_categories(use_cache=False)
    assert cats == ["salario", "pix"]


@pytest.mark.asyncio
async def test_get_income_categories_fallback(finance_service, mock_client):
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    cats = await finance_service.get_income_categories(use_cache=False)
    assert "salario" in cats
    assert "pix" in cats


@pytest.mark.asyncio
async def test_save_income_success(finance_service, mock_client):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "description": "Salário",
        "amount": 5000.0,
        "category": "salario",
        "payment_method": "itau_joao",
    }
    mock_client.post.return_value = mock_response

    details = IncomeDetails(
        fonte="Salário",
        valor=5000.0,
        categoria="salario",
        metodo_recebimento="itau_joao",
    )
    result = await finance_service.save_income(details)

    assert result["amount"] == 5000.0
    mock_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_monthly_summary(finance_service, mock_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "reference_month": "2026-08",
        "total_incomes": 7000.0,
        "total_spents": 3000.0,
        "net_balance": 4000.0,
        "is_positive": True,
        "savings_rate": 57.14,
    }
    mock_client.get.return_value = mock_response

    result = await finance_service.get_monthly_summary("2026-08")
    assert result["total_incomes"] == 7000.0
    assert result["net_balance"] == 4000.0


@pytest.mark.asyncio
async def test_register_income_response(finance_service, mock_client):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "123", "amount": 2000.0}
    mock_client.post.return_value = mock_response

    resp = AssistantResponse(
        response_message="Receita confirmada",
        is_complete=True,
        income_details=IncomeDetails(
            fonte="Pix",
            valor=2000.0,
            categoria="pix",
        ),
    )
    result = await finance_service.register(resp)
    assert result is not None
    assert result["id"] == "123"
