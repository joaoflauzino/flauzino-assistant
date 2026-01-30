import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock
from agent_api.services.finance import FinanceService
from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.spending import SpendingDetails
from agent_api.core.exceptions import (
    FinanceUnreachableError,
    FinanceServerError,
    InvalidSpentError,
)


@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def finance_service(mock_client):
    agent_response = AssistantResponse(
        response_message="Test",
        is_complete=True,
        spending_details=SpendingDetails(
            categoria="comer_fora",
            valor=100.0,
            metodo_pagamento="nubank",
            proprietário="joao_lucas",
            local_compra="Test Location",
        ),
    )
    return FinanceService(agent_response, mock_client)


@pytest.mark.asyncio
async def test_register_finance_unreachable(finance_service, mock_client):
    # Arrange
    # Simulate a connection error when posting to spents
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")

    # Act & Assert
    with pytest.raises(FinanceUnreachableError):
        await finance_service.register()


@pytest.mark.asyncio
async def test_register_invalid_spent_400(finance_service, mock_client):
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
        await finance_service.register()
    assert "Invalid data" in str(exc_info.value)


@pytest.mark.asyncio
async def test_register_invalid_spent_422(finance_service, mock_client):
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
        await finance_service.register()
    assert "Invalid data" in str(exc_info.value)


@pytest.mark.asyncio
async def test_register_finance_server_error(finance_service, mock_client):
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
        await finance_service.register()


@pytest.mark.asyncio
async def test_register_success(finance_service, mock_client):
    # Arrange
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "amount": 100.0}
    mock_client.post.return_value = mock_response

    # Act
    result = await finance_service.register()

    # Assert
    assert result == {"id": 1, "amount": 100.0}
