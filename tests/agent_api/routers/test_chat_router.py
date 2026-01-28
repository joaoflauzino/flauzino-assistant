from unittest.mock import AsyncMock

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from agent_api.main import app
from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.spending import SpendingDetails
from finance_api.schemas.enums import CardEnum, CategoryEnum, NameEnum

# Mark all tests as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_client():
    """Fixture for a test client for the FastAPI app."""
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client


@pytest.fixture
def mock_get_llm_response(mocker):
    """Fixture for mocking the get_llm_response service."""
    return mocker.patch(
        "agent_api.routers.chat.get_llm_response", new_callable=AsyncMock
    )


@pytest.fixture
def mock_save_spent(mocker):
    """Fixture for mocking the save_spent service."""
    return mocker.patch("agent_api.routers.chat.save_spent", new_callable=AsyncMock)


@pytest.fixture
def mock_save_limit(mocker):
    """Fixture for mocking the save_limit service."""
    return mocker.patch("agent_api.routers.chat.save_limit", new_callable=AsyncMock)


async def test_chat_simple_response(test_client, mock_get_llm_response):
    """
    Test a simple chat interaction without database actions.
    """
    # Arrange
    payload = {"message": "Olá", "history": []}
    mock_get_llm_response.return_value = AssistantResponse(
        response_message="Olá! Como posso ajudar?",
        is_complete=False,
    )

    # Act
    response = await test_client.post("/chat", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Olá! Como posso ajudar?"
    assert len(data["history"]) == 2
    assert data["history"][0]["content"] == "Olá"
    assert data["history"][1]["content"] == "Olá! Como posso ajudar?"
    mock_get_llm_response.assert_awaited_once()


async def test_chat_complete_spent_and_save(
    test_client, mock_get_llm_response, mock_save_spent
):
    """
    Test a chat interaction that results in a complete spending record being saved.
    """
    # Arrange
    payload = {"message": "gastei 50 no mercado", "history": []}
    spending_details = SpendingDetails(
        categoria=CategoryEnum.MARKET,
        valor=50.0,
        metodo_pagamento=CardEnum.ITAU,
        proprietário=NameEnum.JOAO_LUCAS,
        local_compra="mercado",
    )
    mock_get_llm_response.return_value = AssistantResponse(
        response_message="Gasto de R$50.0 em mercado registrado.",
        spending_details=spending_details,
        is_complete=True,
    )

    # Act
    response = await test_client.post("/chat", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Gasto de R$50.0 em mercado registrado."
    mock_get_llm_response.assert_awaited_once()
    mock_save_spent.assert_awaited_once_with(spending_details)


async def test_chat_save_spent_fails(
    test_client, mock_get_llm_response, mock_save_spent
):
    """
    Test that an error during saving is appended to the response message.
    """
    # Arrange
    payload = {"message": "gastei 50 no mercado", "history": []}
    spending_details = SpendingDetails(
        categoria=CategoryEnum.MARKET,
        valor=50.0,
        metodo_pagamento=CardEnum.ITAU,
        proprietário=NameEnum.JOAO_LUCAS,
        local_compra="mercado",
    )
    mock_get_llm_response.return_value = AssistantResponse(
        response_message="Gasto de R$50.0 em mercado registrado.",
        spending_details=spending_details,
        is_complete=True,
    )
    mock_save_spent.side_effect = Exception("API connection error")

    # Act
    response = await test_client.post("/chat", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    expected_error_msg = "Gasto de R$50.0 em mercado registrado.\n\n[Sistema: Houve um erro ao salvar o registro no banco de dados: API connection error]"
    assert data["response"] == expected_error_msg
    mock_get_llm_response.assert_awaited_once()
    mock_save_spent.assert_awaited_once()


async def test_chat_llm_fails(test_client, mock_get_llm_response):
    """
    Test that a 500 error is returned if the LLM service fails.
    """
    # Arrange
    payload = {"message": "Olá", "history": []}
    mock_get_llm_response.side_effect = Exception("LLM is down")

    # Act
    response = await test_client.post("/chat", json=payload)

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": "Erro no Agente LLM: LLM is down"}
