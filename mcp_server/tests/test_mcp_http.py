import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def server_url():
    """Sobe o MCP server real via uvicorn num subprocesso e devolve a URL /mcp."""
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "mcp_server.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("MCP server did not start in time")
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.asyncio
async def test_http_streamable_transport_handshake_and_discovery(server_url):
    """Handshake + descoberta de tools via HTTP real (Streamable HTTP)."""
    async with streamable_http_client(server_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            result = await session.list_tools()
            names = {t.name for t in result.tools}
            assert names == {"plot_category_balance", "plot_expense_pie_chart"}
