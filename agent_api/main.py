from fastapi import FastAPI

from agent_api.core.http_client import lifespan
from agent_api.routers.chat import router

app = FastAPI(title="Flauzino Assistant Agent API", lifespan=lifespan)

app.include_router(router)
