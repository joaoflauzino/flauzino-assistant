from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

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


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "graph_api"}


# Register routers
app.include_router(graphs.router)

# Instrument Prometheus metrics and expose on /metrics
Instrumentator(excluded_handlers=["/metrics", "/health"]).instrument(app).expose(
    app, include_in_schema=False, tags=["metrics"]
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
