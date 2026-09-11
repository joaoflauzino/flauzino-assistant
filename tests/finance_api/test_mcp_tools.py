import base64
from unittest.mock import AsyncMock, MagicMock
import pytest
from mcp.server.fastmcp import Image

from finance_api.mcp.server import mcp
from finance_api.mcp.tools import (
    create_spent,
    get_balance_chart,
    get_category_balance,
    list_categories,
)
from finance_api.schemas.categories import CategoryResponse
from finance_api.schemas.limits import CategoryBalance
from finance_api.schemas.spents import SpentResponse


@pytest.mark.asyncio
async def test_mcp_tools_registered():
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "get_category_balance" in tool_names
    assert "create_spent" in tool_names
    assert "list_categories" in tool_names
    assert "get_balance_chart" in tool_names


@pytest.mark.asyncio
async def test_get_category_balance_tool(mocker):
    mock_db = AsyncMock()
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__.return_value = mock_db
    mocker.patch("finance_api.mcp.tools.AsyncSessionLocal", mock_session_local)

    mock_balances = [
        CategoryBalance(
            category="mercado",
            category_display_name="Mercado",
            limit=1000.0,
            spent=300.0,
            available=700.0,
            percentage_used=30.0,
        ),
        CategoryBalance(
            category="lazer",
            category_display_name="Lazer",
            limit=500.0,
            spent=100.0,
            available=400.0,
            percentage_used=20.0,
        ),
    ]

    mocker.patch(
        "finance_api.services.limits.SpendingLimitService.get_balance",
        new_callable=AsyncMock,
        return_value=mock_balances,
    )

    result = await get_category_balance(categories=["mercado"])
    assert len(result) == 1
    assert result[0]["category"] == "mercado"
    assert result[0]["available"] == 700.0


@pytest.mark.asyncio
async def test_create_spent_tool(mocker):
    mock_db = AsyncMock()
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__.return_value = mock_db
    mocker.patch("finance_api.mcp.tools.AsyncSessionLocal", mock_session_local)

    fake_spent = MagicMock(spec=SpentResponse)
    fake_spent.model_dump.return_value = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "category": "mercado",
        "amount": 55.50,
        "item_bought": "Frutas",
        "payment_method": "nubank",
        "location": "Hortifruti",
    }

    mocker.patch(
        "finance_api.services.spents.SpentService.create",
        new_callable=AsyncMock,
        return_value=fake_spent,
    )

    result = await create_spent(
        category="mercado",
        amount=55.50,
        item_bought="Frutas",
        payment_method="nubank",
        location="Hortifruti",
    )

    assert result["category"] == "mercado"
    assert result["amount"] == 55.50
    assert result["item_bought"] == "Frutas"


@pytest.mark.asyncio
async def test_list_categories_tool(mocker):
    mock_db = AsyncMock()
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__.return_value = mock_db
    mocker.patch("finance_api.mcp.tools.AsyncSessionLocal", mock_session_local)

    fake_cat = MagicMock(spec=CategoryResponse)
    fake_cat.model_dump.return_value = {"key": "mercado", "display_name": "Mercado"}

    mocker.patch(
        "finance_api.services.categories.CategoryService.list",
        new_callable=AsyncMock,
        return_value=([fake_cat], 1),
    )

    result = await list_categories()
    assert len(result) == 1
    assert result[0]["key"] == "mercado"


@pytest.mark.asyncio
async def test_get_balance_chart_tool(mocker):
    mocker.patch(
        "finance_api.mcp.tools.get_category_balance",
        new_callable=AsyncMock,
        return_value=[
            {"category_display_name": "Mercado", "limit": 1000, "spent": 200, "available": 800}
        ],
    )

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "image_base64": base64.b64encode(b"fake_png_data").decode("utf-8")
    }
    mock_client.post.return_value = mock_response

    mock_async_client_cls = MagicMock()
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client
    mocker.patch("httpx.AsyncClient", mock_async_client_cls)

    result = await get_balance_chart()
    assert isinstance(result, Image)
    assert result.data == b"fake_png_data"
