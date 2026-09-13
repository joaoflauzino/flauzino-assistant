class GraphAPIError(Exception):
    """Base exception for the Graph API."""

    def __init__(self, message: str = "Graph API Error"):
        self.message = message
        super().__init__(self.message)


class GraphGenerationError(GraphAPIError):
    """Raised when chart/graph generation fails."""

    def __init__(self, message: str = "Graph generation error"):
        self.message = message
        super().__init__(self.message)


class ServiceError(GraphAPIError):
    """Raised for generic internal service errors."""

    def __init__(self, message: str = "Internal Service Error"):
        self.message = message
        super().__init__(self.message)
