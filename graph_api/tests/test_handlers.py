import json
from unittest.mock import MagicMock

import pytest

from graph_api.core.exceptions import GraphAPIError, GraphGenerationError, ServiceError
from graph_api.core.handlers import (
    graph_api_error_handler,
    graph_generation_error_handler,
    service_error_handler,
)


@pytest.mark.parametrize(
    ("handler", "exception", "message"),
    [
        (
            graph_generation_error_handler,
            GraphGenerationError("render failed"),
            "Graph Generation Error",
        ),
        (service_error_handler, ServiceError("service failed"), "Internal Server Error"),
        (graph_api_error_handler, GraphAPIError("graph failed"), "Graph API Error"),
    ],
)
@pytest.mark.asyncio
async def test_graph_exception_handlers_include_exception_detail(
    handler,
    exception: Exception,
    message: str,
) -> None:
    response = await handler(MagicMock(), exception)

    assert response.status_code == 500
    assert json.loads(response.body) == {"message": message, "detail": str(exception)}
