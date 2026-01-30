from fastapi import FastAPI

from agent_api.routers.chat import router

app = FastAPI(title="Flauzino Assistant Agent API")

app.include_router(router)
