from fastapi import FastAPI

from graph_api.core.exceptions import (
    GraphAPIError,
    GraphGenerationError,
    ServiceError,
)
from graph_api.core.handlers import (
    graph_api_error_handler,
    graph_generation_error_handler,
    service_error_handler,
)
from graph_api.routers import graphs

app = FastAPI(title="Flauzino Assistant Graph API")

# Register global exception handlers
app.add_exception_handler(GraphGenerationError, graph_generation_error_handler)
app.add_exception_handler(ServiceError, service_error_handler)
app.add_exception_handler(GraphAPIError, graph_api_error_handler)

# Register routers
app.include_router(graphs.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
