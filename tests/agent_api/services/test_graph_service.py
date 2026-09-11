from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from agent_api.core.exceptions import GraphServiceError
from agent_api.services.graph import GraphService


@pytest.mark.asyncio
async def test_generate_bar_chart_calls_correct_endpoint():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"image_base64": "base64_bar_data"}
    mock_client.post.return_value = mock_response

    service = GraphService(client=mock_client)
    balances = [{"category_display_name": "Mercado", "limit": 1000, "spent": 200, "available": 800}]

    result = await service.generate_chart(
        chart_type="plot_category_balance",
        balances=balances,
        mode="saldo",
    )

    assert result == "base64_bar_data"
    mock_client.post.assert_awaited_once()
    call_args = mock_client.post.call_args
    assert call_args.args[0].endswith("/graphs/bar")
    assert call_args.kwargs["json"]["mode"] == "saldo"
    assert call_args.kwargs["json"]["balances"] == balances


@pytest.mark.asyncio
async def test_generate_pie_chart_calls_correct_endpoint():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"image_base64": "base64_pie_data"}
    mock_client.post.return_value = mock_response

    service = GraphService(client=mock_client)
    balances = [{"category_display_name": "Mercado", "limit": 1000, "spent": 200, "available": 800}]

    result = await service.generate_chart(
        chart_type="plot_expense_pie_chart",
        balances=balances,
    )

    assert result == "base64_pie_data"
    mock_client.post.assert_awaited_once()
    call_args = mock_client.post.call_args
    assert call_args.args[0].endswith("/graphs/pie")
    assert call_args.kwargs["json"]["balances"] == balances


@pytest.mark.asyncio
async def test_generate_chart_error_raises_graph_service_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")

    service = GraphService(client=mock_client)
    with pytest.raises(GraphServiceError) as exc_info:
        await service.generate_chart("plot_category_balance", [])

    assert "Failed to generate graph" in str(exc_info.value)
