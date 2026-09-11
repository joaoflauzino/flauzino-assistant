from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from agent_api.core.exceptions import (
    FinanceServerError,
    FinanceUnreachableError,
    InvalidSpentError,
)
from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.spending import SpendingDetails
from agent_api.services.finance import FinanceService


@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def sample_agent_response():
    return AssistantResponse(
        response_message="Test",
        is_complete=True,
        spending_details=SpendingDetails(
            categoria="comer_fora",
            valor=100.0,
            metodo_pagamento="nubank",
            item_comprado="Test Item",
            local_compra="Test Location",
        ),
    )


@pytest.fixture
def finance_service(mock_client):
    return FinanceService(client=mock_client)


@pytest.mark.asyncio
async def test_register_finance_unreachable(
    finance_service, sample_agent_response, mock_client
):
    # Arrange
    # Simulate a connection error when posting to spents
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")

    # Act & Assert
    with pytest.raises(FinanceUnreachableError):
        await finance_service.register(sample_agent_response)


@pytest.mark.asyncio
async def test_register_invalid_spent_400(
    finance_service, sample_agent_response, mock_client
):
    # Arrange
    # Simulate a 400 Bad Request
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Invalid Category"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "400 Bad Request", request=MagicMock(), response=mock_response
    )
    mock_client.post.return_value = mock_response

    # Act & Assert
    with pytest.raises(InvalidSpentError) as exc_info:
        await finance_service.register(sample_agent_response)
    assert "Invalid data" in str(exc_info.value)


@pytest.mark.asyncio
async def test_register_invalid_spent_422(
    finance_service, sample_agent_response, mock_client
):
    # Arrange
    # Simulate a 422 Unprocessable Entity
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.text = "Validation Error"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "422 Unprocessable Entity", request=MagicMock(), response=mock_response
    )
    mock_client.post.return_value = mock_response

    # Act & Assert
    with pytest.raises(InvalidSpentError) as exc_info:
        await finance_service.register(sample_agent_response)
    assert "Invalid data" in str(exc_info.value)


@pytest.mark.asyncio
async def test_register_finance_server_error(
    finance_service, sample_agent_response, mock_client
):
    # Arrange
    # Simulate a 500 Internal Server Error
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error", request=MagicMock(), response=mock_response
    )
    mock_client.post.return_value = mock_response

    # Act & Assert
    with pytest.raises(FinanceServerError):
        await finance_service.register(sample_agent_response)


@pytest.mark.asyncio
async def test_register_success(finance_service, sample_agent_response, mock_client):
    # Arrange
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "amount": 100.0}
    mock_client.post.return_value = mock_response

    # Act
    result = await finance_service.register(sample_agent_response)

    # Assert
    assert result == {"id": 1, "amount": 100.0}


@pytest.mark.asyncio
async def test_get_balances_success(mock_client):
    # Arrange
    service = FinanceService(client=mock_client)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"category": "mercado", "limit": 1000.0, "spent": 200.0, "available": 800.0}
    ]
    mock_client.get.return_value = mock_response

    # Act
    balances = await service.get_balances(categories=["mercado"])

    # Assert
    assert len(balances) == 1
    assert balances[0]["category"] == "mercado"
    mock_client.get.assert_awaited_once()
    call_args = mock_client.get.call_args
    assert "categories=mercado" in str(
        call_args
    ) or call_args.kwargs.get("params") == {"categories": "mercado"}


@pytest.mark.asyncio
async def test_get_categories_success(mock_client):
    service = FinanceService(client=mock_client)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [{"key": "alimentacao"}, {"key": "lazer"}]
    }
    mock_client.get.return_value = mock_response

    # Use cache=False to test network retrieval
    categories = await service.get_categories(use_cache=False)
    assert categories == ["alimentacao", "lazer"]


@pytest.mark.asyncio
async def test_get_payment_methods_success(mock_client):
    service = FinanceService(client=mock_client)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [{"key": "pix"}, {"key": "nubank"}]
    }
    mock_client.get.return_value = mock_response

    # Use cache=False to test network retrieval
    methods = await service.get_payment_methods(use_cache=False)
    assert methods == ["pix", "nubank"]
