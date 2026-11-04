from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from agent_api.core.exceptions import (
    FinanceServerError,
    FinanceUnreachableError,
    InvalidSpentError,
)
from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.finance import (
    DEFAULT_ACCOUNTS,
    DEFAULT_CATEGORIES,
    DEFAULT_CREDIT_CARDS,
    DEFAULT_PAYMENT_METHODS,
)
from agent_api.schemas.limit import LimitDetails
from agent_api.schemas.spending import SpendingDetails
from agent_api.services.clients.finance import FinanceService
from agent_api.services.protocols import FinanceServiceProtocol


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


def test_finance_service_satisfies_protocol(finance_service: FinanceService) -> None:
    svc: FinanceServiceProtocol = finance_service
    assert hasattr(svc, "get_categories")
    assert hasattr(svc, "register")


@pytest.mark.asyncio
async def test_register_finance_unreachable(finance_service, sample_agent_response, mock_client):
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")

    with pytest.raises(FinanceUnreachableError):
        await finance_service.register(sample_agent_response)


@pytest.mark.asyncio
async def test_register_invalid_spent_400(finance_service, sample_agent_response, mock_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Invalid Category"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "400 Bad Request", request=MagicMock(), response=mock_response
    )
    mock_client.post.return_value = mock_response

    with pytest.raises(InvalidSpentError) as exc_info:
        await finance_service.register(sample_agent_response)
    assert "Invalid data" in str(exc_info.value)


@pytest.mark.asyncio
async def test_register_invalid_spent_422(finance_service, sample_agent_response, mock_client):
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.text = "Validation Error"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "422 Unprocessable Entity", request=MagicMock(), response=mock_response
    )
    mock_client.post.return_value = mock_response

    with pytest.raises(InvalidSpentError) as exc_info:
        await finance_service.register(sample_agent_response)
    assert "Invalid data" in str(exc_info.value)


@pytest.mark.asyncio
async def test_register_finance_server_error(finance_service, sample_agent_response, mock_client):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error", request=MagicMock(), response=mock_response
    )
    mock_client.post.return_value = mock_response

    with pytest.raises(FinanceServerError):
        await finance_service.register(sample_agent_response)


@pytest.mark.asyncio
async def test_register_success(finance_service, sample_agent_response, mock_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "amount": 100.0}
    mock_client.post.return_value = mock_response

    result = await finance_service.register(sample_agent_response)
    assert result == {"id": 1, "amount": 100.0}


@pytest.mark.asyncio
async def test_register_limit_and_empty_response(finance_service, mock_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 99, "category": "lazer", "amount": 500.0}
    mock_client.post.return_value = mock_response

    limit_resp = AssistantResponse(
        response_message="Limite salvo",
        is_complete=True,
        limit_details=LimitDetails(categoria="lazer", valor=500.0),
    )
    res_limit = await finance_service.register(limit_resp)
    assert res_limit == {"id": 99, "category": "lazer", "amount": 500.0}

    empty_resp = AssistantResponse(response_message="Olá", is_complete=False)
    assert await finance_service.register(empty_resp) is None


@pytest.mark.asyncio
async def test_get_balances_success_and_non_200(mock_client):
    service = FinanceService(client=mock_client)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"category": "mercado", "limit": 1000.0, "spent": 200.0, "available": 800.0}
    ]
    mock_client.get.return_value = mock_response

    balances = await service.get_balances(categories=["mercado"], reference_month="2026-11")
    assert len(balances) == 1
    assert balances[0]["category"] == "mercado"

    mock_response_404 = MagicMock()
    mock_response_404.status_code = 404
    mock_client.get.return_value = mock_response_404
    assert await service.get_balances() == []


@pytest.mark.asyncio
async def test_get_monthly_summary_non_200(mock_client):
    service = FinanceService(client=mock_client)
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_client.get.return_value = mock_response

    assert await service.get_monthly_summary(reference_month="2026-11") == {}


@pytest.mark.asyncio
async def test_get_categories_success_cache_and_fallback(mock_client):
    service = FinanceService(client=mock_client)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [{"key": "alimentacao"}, {"key": "lazer"}]}
    mock_client.get.return_value = mock_response

    categories = await service.get_categories(use_cache=False)
    assert categories == ["alimentacao", "lazer"]
    # Second call with use_cache=True hits memory cache
    assert await service.get_categories(use_cache=True) == ["alimentacao", "lazer"]

    # Fallback when cache is cleared and API errors
    FinanceService._cached_categories = None
    FinanceService._categories_expiry = 0.0
    mock_client.get.side_effect = httpx.ConnectError("API down")
    assert await service.get_categories(use_cache=False) == DEFAULT_CATEGORIES


@pytest.mark.asyncio
async def test_get_income_categories_cache_hit(mock_client):
    service = FinanceService(client=mock_client)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [{"key": "salario"}]}
    mock_client.get.return_value = mock_response

    assert await service.get_income_categories(use_cache=False) == ["salario"]
    assert await service.get_income_categories(use_cache=True) == ["salario"]


@pytest.mark.asyncio
async def test_get_payment_methods_success_cache_and_fallback(mock_client):
    service = FinanceService(client=mock_client)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [{"key": "pix"}, {"key": "nubank"}]}
    mock_client.get.return_value = mock_response

    methods = await service.get_payment_methods(use_cache=False)
    assert methods == ["pix", "nubank"]
    assert await service.get_payment_methods(use_cache=True) == ["pix", "nubank"]

    FinanceService._cached_payment_methods = None
    FinanceService._payment_methods_expiry = 0.0
    mock_client.get.side_effect = httpx.ConnectError("API down")
    assert await service.get_payment_methods(use_cache=False) == DEFAULT_PAYMENT_METHODS


@pytest.mark.asyncio
async def test_get_accounts_success_and_cache(mock_client):
    service = FinanceService(client=mock_client)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [{"key": "itau_joao"}, {"key": "nubank_joao"}]}
    mock_client.get.return_value = mock_response

    accounts = await service.get_accounts(use_cache=False)
    assert accounts == ["itau_joao", "nubank_joao"]
    assert await service.get_accounts(use_cache=True) == ["itau_joao", "nubank_joao"]


@pytest.mark.asyncio
async def test_get_accounts_fallback(mock_client):
    FinanceService._cached_accounts = None
    FinanceService._accounts_expiry = 0.0
    service = FinanceService(client=mock_client)
    mock_client.get.side_effect = httpx.ConnectError("API down")

    accounts = await service.get_accounts(use_cache=False)
    assert accounts == DEFAULT_ACCOUNTS


@pytest.mark.asyncio
async def test_get_credit_cards_success_and_cache(mock_client):
    service = FinanceService(client=mock_client)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [{"key": "itau_card_joao"}, {"key": "c6_card_joao"}]
    }
    mock_client.get.return_value = mock_response

    cards = await service.get_credit_cards(use_cache=False)
    assert cards == ["itau_card_joao", "c6_card_joao"]
    assert await service.get_credit_cards(use_cache=True) == ["itau_card_joao", "c6_card_joao"]


@pytest.mark.asyncio
async def test_get_credit_cards_fallback(mock_client):
    FinanceService._cached_credit_cards = None
    FinanceService._credit_cards_expiry = 0.0
    service = FinanceService(client=mock_client)
    mock_client.get.side_effect = httpx.ConnectError("API down")

    cards = await service.get_credit_cards(use_cache=False)
    assert cards == DEFAULT_CREDIT_CARDS


@pytest.mark.asyncio
async def test_post_to_finance_api_propagates_correlation_id(mock_client):
    from agent_api.core.correlation import CORRELATION_HEADER, set_request_id

    service = FinanceService(client=mock_client)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "spent-123"}
    mock_client.post.return_value = mock_response

    set_request_id("my-trace-id-abc")
    await service._post_to_finance_api("spents", {"amount": 10})

    mock_client.post.assert_called_once()
    called_headers = mock_client.post.call_args.kwargs.get("headers", {})
    assert called_headers.get(CORRELATION_HEADER) == "my-trace-id-abc"
