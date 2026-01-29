from fastapi import FastAPI

from finance_api.core.http_client import lifespan
from finance_api.routers import limits, spents

app = FastAPI(title="Flauzino Assistant API", lifespan=lifespan)

app.include_router(spents.router, prefix="/spents", tags=["spents"])
app.include_router(limits.router, prefix="/limits", tags=["limits"])
