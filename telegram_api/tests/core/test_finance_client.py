"""Unit tests for the finance_api/graph_api client."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from telegram_api.core.finance_client import filter_balances, get_balance_graph

get_client = "telegram_api.core.finance_client.get_http_client"

BALANCES = [
    {"category": "mercado", "category_display_name": "Mercado", "spent": 100},
    {"category": "lazer", "category_display_name": "Lazer", "spent": 50},
]


@pytest.mark.asyncio
@patch(get_client)
async def test_get_balance_graph_404(mock_get_client):
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_client.get.return_value = mock_resp
    mock_get_client.return_value = mock_client

    result = await get_balance_graph()
    assert result is None
    mock_client.post.assert_not_called()


@pytest.mark.asyncio
@patch(get_client)
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
@patch(get_client)
async def test_get_balance_graph_success(mock_get_client):
    mock_client = AsyncMock()

    mock_fin_resp = MagicMock()
    mock_fin_resp.status_code = 200
    mock_fin_resp.json.return_value = BALANCES
    mock_client.get.return_value = mock_fin_resp

    raw_img = b"fake_png_data"
    mock_graph_resp = MagicMock()
    mock_graph_resp.status_code = 200
    mock_graph_resp.json.return_value = {"image_base64": base64.b64encode(raw_img).decode("utf-8")}
    mock_client.post.return_value = mock_graph_resp

    mock_get_client.return_value = mock_client

    result = await get_balance_graph(categories={"mercado"}, mode="saldo")
    assert result == raw_img

    mock_client.post.assert_called_once()
    called_json = mock_client.post.call_args.kwargs["json"]
    assert called_json["mode"] == "saldo"
    assert len(called_json["balances"]) == 1
    assert called_json["balances"][0]["category"] == "mercado"


@pytest.mark.asyncio
@patch(get_client)
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


def test_filter_balances_returns_everything_without_a_filter():
    assert filter_balances(BALANCES, None) == BALANCES
    assert filter_balances(BALANCES, set()) == BALANCES


def test_filter_balances_matches_category_key_case_insensitively():
    filtered = filter_balances(BALANCES, {"MERCADO"})

    assert [balance["category"] for balance in filtered] == ["mercado"]


def test_filter_balances_matches_display_name():
    filtered = filter_balances(BALANCES, ["lazer"])

    assert [balance["category"] for balance in filtered] == ["lazer"]


def test_filter_balances_falls_back_to_every_balance_when_nothing_matches():
    assert filter_balances(BALANCES, {"inexistente"}) == BALANCES
