from fastapi import FastAPI

from finance_api.routers import limits, spents
from finance_api.core.exceptions import DatabaseError, EntityNotFoundError
from finance_api.core.handlers import database_error_handler, entity_not_found_handler

app = FastAPI(title="Flauzino Assistant API")

app.add_exception_handler(DatabaseError, database_error_handler)
app.add_exception_handler(EntityNotFoundError, entity_not_found_handler)

app.include_router(spents.router, prefix="/spents", tags=["spents"])
app.include_router(limits.router, prefix="/limits", tags=["limits"])
