from fastapi import FastAPI

from agent_api.core.exceptions import (
    FinanceUnreachableError,
    InvalidSpentError,
    FinanceServerError,
    LLMProviderError,
    LLMParsingError,
    LLMUnknownError,
    DatabaseError,
)
from agent_api.core.handlers import (
    finance_unreachable_handler,
    invalid_spent_handler,
    finance_server_error_handler,
    llm_provider_handler,
    llm_parsing_handler,
    llm_unknown_handler,
    database_error_handler,
)

from agent_api.routers.chat import router

app = FastAPI(title="Flauzino Assistant Agent API")

app.add_exception_handler(FinanceUnreachableError, finance_unreachable_handler)
app.add_exception_handler(InvalidSpentError, invalid_spent_handler)
app.add_exception_handler(FinanceServerError, finance_server_error_handler)
app.add_exception_handler(LLMProviderError, llm_provider_handler)
app.add_exception_handler(LLMParsingError, llm_parsing_handler)
app.add_exception_handler(LLMUnknownError, llm_unknown_handler)
app.add_exception_handler(DatabaseError, database_error_handler)

app.include_router(router)
