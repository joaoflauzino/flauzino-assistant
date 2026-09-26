import base64
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from telegram_api.core.http_client import get_balance_graph


@pytest.mark.asyncio
@patch("telegram_api.core.http_client.get_http_client")
async def test_get_balance_graph_404(mock_get_client):
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_client.get.return_value = mock_resp
    mock_get_client.return_value = mock_client

    result = await get_balance_graph()
    assert result is None


@pytest.mark.asyncio
@patch("telegram_api.core.http_client.get_http_client")
async def test_get_balance_graph_empty_balances(mock_get_client):
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []
    mock_client.get.return_value = mock_resp
    mock_get_client.return_value = mock_client

    result = await get_balance_graph()
    assert result is None


@pytest.mark.asyncio
@patch("telegram_api.core.http_client.get_http_client")
async def test_get_balance_graph_success(mock_get_client):
    mock_client = AsyncMock()

    # Finance mock
    mock_fin_resp = MagicMock()
    mock_fin_resp.status_code = 200
    mock_fin_resp.json.return_value = [
        {"category": "mercado", "category_display_name": "Mercado", "spent": 100},
        {"category": "lazer", "category_display_name": "Lazer", "spent": 50},
    ]
    mock_client.get.return_value = mock_fin_resp

    # Graph mock
    raw_img = b"fake_png_data"
    b64_img = base64.b64encode(raw_img).decode("utf-8")
    mock_graph_resp = MagicMock()
    mock_graph_resp.status_code = 200
    mock_graph_resp.json.return_value = {"image_base64": b64_img}
    mock_client.post.return_value = mock_graph_resp

    mock_get_client.return_value = mock_client

    result = await get_balance_graph(categories={"mercado"}, mode="saldo")
    assert result == raw_img

    # Verify post payload filtered only mercado
    mock_client.post.assert_called_once()
    called_json = mock_client.post.call_args.kwargs["json"]
    assert called_json["mode"] == "saldo"
    assert len(called_json["balances"]) == 1
    assert called_json["balances"][0]["category"] == "mercado"


@pytest.mark.asyncio
@patch("telegram_api.core.http_client.get_http_client")
async def test_get_balance_graph_missing_image_in_response(mock_get_client):
    mock_client = AsyncMock()

    mock_fin_resp = MagicMock()
    mock_fin_resp.status_code = 200
    mock_fin_resp.json.return_value = [{"category": "mercado"}]
    mock_client.get.return_value = mock_fin_resp

    mock_graph_resp = MagicMock()
    mock_graph_resp.status_code = 200
    mock_graph_resp.json.return_value = {}
    mock_client.post.return_value = mock_graph_resp

    mock_get_client.return_value = mock_client

    result = await get_balance_graph()
    assert result is None


@pytest.mark.asyncio
@patch("telegram_api.core.http_client.get_http_client")
async def test_send_message_to_agent_includes_correlation_header(mock_get_client):
    from telegram_api.core.correlation import CORRELATION_HEADER, set_request_id
    from telegram_api.core.http_client import send_message_to_agent

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "ok"}
    mock_client.post.return_value = mock_resp
    mock_get_client.return_value = mock_client

    set_request_id("tg-trace-xyz")
    res = await send_message_to_agent("olá")
    assert res == {"response": "ok"}

    mock_client.post.assert_called_once()
    headers = mock_client.post.call_args.kwargs.get("headers", {})
    assert headers.get(CORRELATION_HEADER) == "tg-trace-xyz"
