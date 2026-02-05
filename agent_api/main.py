from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent_api.core.exceptions import (
    FinanceUnreachableError,
    FinanceServerError,
    InvalidSpentError,
    LLMProviderError,
    ServiceError,
)
from agent_api.core.handlers import (
    finance_unreachable_handler,
    finance_server_error_handler,
    invalid_spent_handler,
    llm_provider_handler,
    service_error_handler,
)
from agent_api.routers import chat
from agent_api.settings import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(FinanceUnreachableError, finance_unreachable_handler)
app.add_exception_handler(FinanceServerError, finance_server_error_handler)
app.add_exception_handler(InvalidSpentError, invalid_spent_handler)
app.add_exception_handler(LLMProviderError, llm_provider_handler)
app.add_exception_handler(ServiceError, service_error_handler)

# Register routers
app.include_router(chat.router, prefix="/chat", tags=["chat"])
