from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "graph-generator",
    # Host não-localhost evita que o FastMCP ative a proteção anti DNS-rebinding,
    # que bloquearia requisições vindas de outros serviços (ex: agent_api -> mcp_server:8002).
    host="0.0.0.0",
)
