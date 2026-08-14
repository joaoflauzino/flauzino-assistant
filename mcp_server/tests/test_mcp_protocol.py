import base64

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import ImageContent, TextContent

from mcp_server.core.mcp import mcp

# Importa o serviço para registrar as tools via decorator
import mcp_server.services.mcp_service  # noqa: F401

SAMPLE_BALANCE = [
    {
        "category": "mercado",
        "category_display_name": "Mercado",
        "limit": 1000.0,
        "spent": 300.0,
        "available": 700.0,
    },
    {
        "category": "lazer",
        "category_display_name": "Lazer",
        "limit": 500.0,
        "spent": 0.0,
        "available": 500.0,
    },
]


async def _connected_session():
    return create_connected_server_and_client_session(mcp)


@pytest.mark.asyncio
async def test_list_tools_discovers_both_tools():
    """tools/list deve retornar as duas ferramentas registradas."""
    async with await _connected_session() as session:
        result = await session.list_tools()
        names = {t.name for t in result.tools}
        assert names == {"plot_category_balance", "plot_expense_pie_chart"}


@pytest.mark.asyncio
async def test_list_tools_includes_descriptions():
    """As tools devem expor descrições e schema de entrada para o cliente."""
    async with await _connected_session() as session:
        result = await session.list_tools()
        by_name = {t.name: t for t in result.tools}

        balance = by_name["plot_category_balance"]
        assert balance.description
        props = balance.inputSchema.get("properties", {})
        assert "reference_month" in props
        assert "categories" in props
        assert "mode" in props

        pie = by_name["plot_expense_pie_chart"]
        assert pie.description
        assert "categories" in pie.inputSchema.get("properties", {})


@pytest.mark.asyncio
async def test_call_tool_returns_image_content(mocker):
    """tools/call de plot_category_balance deve retornar uma imagem PNG base64."""
    mocker.patch("mcp_server.services.finance_service.fetch_balance", return_value=SAMPLE_BALANCE)

    async with await _connected_session() as session:
        result = await session.call_tool("plot_category_balance", arguments={"mode": "saldo"})
        assert result.isError is False
        assert len(result.content) == 1
        content = result.content[0]
        assert isinstance(content, ImageContent)
        assert content.type == "image"
        assert content.mimeType == "image/png"
        raw = base64.b64decode(content.data)
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_call_tool_pie_chart_returns_image(mocker):
    """tools/call de plot_expense_pie_chart deve retornar uma imagem PNG base64."""
    mocker.patch("mcp_server.services.finance_service.fetch_balance", return_value=SAMPLE_BALANCE)

    async with await _connected_session() as session:
        result = await session.call_tool("plot_expense_pie_chart", arguments={})
        assert result.isError is False
        content = result.content[0]
        assert isinstance(content, ImageContent)
        raw = base64.b64decode(content.data)
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_call_tool_without_balances_returns_text(mocker):
    """Sem dados, a tool deve responder com texto explicando, não com imagem."""
    mocker.patch("mcp_server.services.finance_service.fetch_balance", return_value=[])

    async with await _connected_session() as session:
        result = await session.call_tool("plot_category_balance", arguments={})
        assert result.isError is False
        assert len(result.content) == 1
        content = result.content[0]
        assert isinstance(content, TextContent)
        assert "Não encontrei" in content.text
