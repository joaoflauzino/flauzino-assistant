from fastapi import FastAPI

from agent_api.core.exceptions import (
    FinanceUnreachableError,
    FinanceServerError,
    InvalidSpentError,
    LLMProviderError,
    ServiceError,
    OCRProcessingError,
    InvalidImageError,
)
from agent_api.core.handlers import (
    finance_unreachable_handler,
    finance_server_error_handler,
    invalid_spent_handler,
    llm_provider_handler,
    service_error_handler,
    ocr_processing_handler,
    invalid_image_handler,
)

from agent_api.routers.chat import router as chat_router
from agent_api.routers.ocr import router as ocr_router

app = FastAPI(title="Flauzino Assistant Agent API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(FinanceUnreachableError, finance_unreachable_handler)
app.add_exception_handler(FinanceServerError, finance_server_error_handler)
app.add_exception_handler(InvalidSpentError, invalid_spent_handler)
app.add_exception_handler(LLMProviderError, llm_provider_handler)
app.add_exception_handler(ServiceError, service_error_handler)
app.add_exception_handler(OCRProcessingError, ocr_processing_handler)
app.add_exception_handler(InvalidImageError, invalid_image_handler)

app.include_router(chat_router)
app.include_router(ocr_router)
