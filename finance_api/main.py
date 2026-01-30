from fastapi import FastAPI

from finance_api.routers import limits, spents

app = FastAPI(title="Flauzino Assistant API")

app.include_router(spents.router, prefix="/spents", tags=["spents"])
app.include_router(limits.router, prefix="/limits", tags=["limits"])
