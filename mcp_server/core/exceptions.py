class MCPServerError(Exception):
    """Base exception for the MCP Server."""

    def __init__(self, message: str = "MCP Server Error"):
        self.message = message
        super().__init__(self.message)


class FinanceClientError(MCPServerError):
    """Raised when communication with the Finance API fails."""

    def __init__(self, message: str = "Finance API communication error"):
        self.message = message
        super().__init__(self.message)


class GraphGenerationError(MCPServerError):
    """Raised when chart/graph generation fails."""

    def __init__(self, message: str = "Graph generation error"):
        self.message = message
        super().__init__(self.message)


class ServiceError(MCPServerError):
    """Raised for generic internal service errors."""

    def __init__(self, message: str = "Internal Service Error"):
        self.message = message
        super().__init__(self.message)
