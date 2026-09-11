from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

# Instância singleton do FastMCP para a finance_api
# host="0.0.0.0" evita proteção contra DNS-rebinding em redes Docker/locais
mcp = FastMCP("flauzino-finance", host="0.0.0.0")


class MCPStreamableApp:
    """Wrapper ASGI que permite recriar o StreamableHTTPSessionManager a cada ciclo de vida (lifespan).

    Necessário pois o StreamableHTTPSessionManager não permite chamar .run() mais de uma vez na mesma instância
    (o que quebrava suítes de testes que reiniciam o lifespan do FastAPI repetidamente).
    """

    def __init__(self):
        self.session_manager: StreamableHTTPSessionManager | None = None
        self._asgi_app: StreamableHTTPASGIApp | None = None

    def create_manager(self) -> StreamableHTTPSessionManager:
        self.session_manager = StreamableHTTPSessionManager(
            app=mcp._mcp_server,
            json_response=mcp.settings.json_response,
            stateless=mcp.settings.stateless_http,
            security_settings=mcp.settings.transport_security,
        )
        self._asgi_app = StreamableHTTPASGIApp(self.session_manager)
        return self.session_manager

    async def __call__(self, scope, receive, send):
        if self._asgi_app is None:
            self.create_manager()
        await self._asgi_app(scope, receive, send)


mcp_streamable_app = MCPStreamableApp()
