from unittest.mock import AsyncMock

import pytest
from mcp.types import CallToolResult, ImageContent, TextContent

from agent_api.services import mcp_client


@pytest.fixture
def mock_mcp_transport(mocker):
    """Mocka o transporte HTTP (streamable_http_client) e o ClientSession."""
    transport = AsyncMock()
    transport.__aenter__.return_value = (AsyncMock(), AsyncMock(), AsyncMock())
    transport_mock = mocker.patch(
        "agent_api.services.mcp_client.streamable_http_client", return_value=transport
    )

    session = AsyncMock()
    session_cls = mocker.patch("agent_api.services.mcp_client.ClientSession")
    session_cls.return_value.__aenter__.return_value = session

    return transport_mock, session


@pytest.mark.asyncio
async def test_list_tools_uses_http_mcp_endpoint(mock_mcp_transport):
    transport_mock, session = mock_mcp_transport
    session.list_tools.return_value.tools = ["tool1", "tool2"]

    result = await mcp_client.list_tools()

    # A comunicação deve ser via HTTP no endpoint /mcp
    url = transport_mock.call_args.args[0]
    assert url.endswith("/mcp")
    assert result == ["tool1", "tool2"]
    session.initialize.assert_awaited_once()
    session.list_tools.assert_awaited_once()


@pytest.mark.asyncio
async def test_call_tool_extracts_image_and_text(mock_mcp_transport):
    _, session = mock_mcp_transport
    session.call_tool.return_value = CallToolResult(
        content=[
            ImageContent(type="image", data="aGVsbG8=", mimeType="image/png"),
            TextContent(type="text", text="ok"),
        ]
    )

    result = await mcp_client.call_tool("plot_category_balance", arguments={"mode": "saldo"})

    assert result.image_base64 == "aGVsbG8="
    assert result.text == "ok"
    assert result.is_error is False
    session.call_tool.assert_awaited_once_with("plot_category_balance", arguments={"mode": "saldo"})


@pytest.mark.asyncio
async def test_call_tool_extracts_text_only(mock_mcp_transport):
    _, session = mock_mcp_transport
    session.call_tool.return_value = CallToolResult(
        content=[TextContent(type="text", text="Sem dados")]
    )

    result = await mcp_client.call_tool("plot_category_balance", arguments={})

    assert result.image_base64 is None
    assert result.text == "Sem dados"
    assert result.is_error is False


@pytest.mark.asyncio
async def test_call_tool_marks_error(mock_mcp_transport):
    _, session = mock_mcp_transport
    session.call_tool.return_value = CallToolResult(
        isError=True, content=[TextContent(type="text", text="erro interno")]
    )

    result = await mcp_client.call_tool("plot_category_balance", arguments={})

    assert result.is_error is True
    assert result.text == "erro interno"
