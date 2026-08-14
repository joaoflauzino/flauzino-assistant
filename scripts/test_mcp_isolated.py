"""Testa o MCP server de forma isolada, ponta a ponta via HTTP (Streamable HTTP).

Uso:
    python scripts/test_mcp_isolated.py [--url http://localhost:8002/mcp]

O script conecta no servidor, descobre as tools via tools/list e chama uma delas.
Se for gerada uma imagem, ela é salva em /tmp/mcp_graph_test.png para inspeção visual.
"""

import argparse
import asyncio
import base64
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def run(url: str, tool: str) -> int:
    print(f"Conectando em {url} ...")
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Handshake (initialize) OK")

            tools = await session.list_tools()
            print("\nTools descobertas via tools/list:")
            for t in tools.tools:
                print(f"  - {t.name}")
                print(f"      descricao: {t.description}")

            print(f"\nChamando tool '{tool}' ...")
            result = await session.call_tool(tool, arguments={})

            print(f"isError: {result.isError}")
            for item in result.content:
                if getattr(item, "type", "") == "image":
                    data = base64.b64decode(item.data)
                    out = Path("/tmp/mcp_graph_test.png")
                    out.write_bytes(data)
                    print(f"Imagem recebida e salva em {out} ({len(data)} bytes)")
                elif getattr(item, "type", "") == "text":
                    print(f"Resposta de texto: {item.text}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Teste isolado do MCP server")
    parser.add_argument(
        "--url", default="http://localhost:8002/mcp", help="Endpoint /mcp do servidor"
    )
    parser.add_argument(
        "--tool",
        default="plot_category_balance",
        choices=["plot_category_balance", "plot_expense_pie_chart"],
        help="Tool a ser chamada",
    )
    args = parser.parse_args()

    try:
        raise SystemExit(asyncio.run(run(args.url, args.tool)))
    except KeyboardInterrupt:
        raise SystemExit(130)


if __name__ == "__main__":
    main()
