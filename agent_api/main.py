import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_api.core.database import AsyncSessionLocal
from agent_api.core.exceptions import (
    AudioProcessingError,
    FinanceServerError,
    FinanceUnreachableError,
    InvalidAudioError,
    InvalidImageError,
    InvalidSpentError,
    LLMProviderError,
    OCRProcessingError,
    ServiceError,
)
from agent_api.core.handlers import (
    audio_processing_handler,
    finance_server_error_handler,
    finance_unreachable_handler,
    invalid_audio_handler,
    invalid_image_handler,
    invalid_spent_handler,
    llm_provider_handler,
    ocr_processing_handler,
    service_error_handler,
)
from agent_api.core.logger import get_logger
from agent_api.repositories.chat_repository import ChatRepository
from agent_api.routers.audio import router as audio_router
from agent_api.routers.chat import router as chat_router
from agent_api.routers.ocr import router as ocr_router

logger = get_logger(__name__)

CLEANUP_INTERVAL_SECONDS = 600  # 10 minutes
STALE_SESSION_MAX_AGE_MINUTES = 30


async def _session_cleanup_loop() -> None:
    """Periodically clean up stale chat sessions."""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            async with AsyncSessionLocal() as db_session:
                repo = ChatRepository(db_session)
                count = await repo.cleanup_stale_sessions(STALE_SESSION_MAX_AGE_MINUTES)
                if count:
                    logger.info(f"Cleaned up {count} stale chat sessions")
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Manage startup/shutdown lifecycle events."""
    cleanup_task = asyncio.create_task(_session_cleanup_loop())
    logger.info("Started session cleanup background task")
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("Session cleanup background task cancelled")


app = FastAPI(title="Flauzino Assistant Agent API", lifespan=lifespan)

allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
app.add_exception_handler(AudioProcessingError, audio_processing_handler)
app.add_exception_handler(InvalidAudioError, invalid_audio_handler)

app.include_router(chat_router)
app.include_router(ocr_router)
app.include_router(audio_router)
