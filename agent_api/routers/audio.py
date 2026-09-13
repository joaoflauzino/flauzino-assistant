"""Audio Router for processing voice messages and audio files."""

from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from agent_api.core.database import get_db
from agent_api.core.http_client import get_http_client
from agent_api.core.logger import get_logger
from agent_api.schemas.dtos import ChatResponse
from agent_api.services.audio import transcribe_audio, validate_audio_file
from agent_api.services.chat import ChatService

logger = get_logger(__name__)

router = APIRouter(prefix="/audio", tags=["Audio"])


@router.post("/process-audio", response_model=ChatResponse)
async def process_audio_file(
    file: UploadFile = File(..., description="Audio file"),
    session_id: Optional[str] = Form(None, description="Chat session ID for context"),
    platform: Optional[str] = Form(None, description="Platform originating the request"),
    client: httpx.AsyncClient = Depends(get_http_client),
    db: AsyncSession = Depends(get_db),
):
    """Process an audio file and start/continue a chat session."""
    logger.info(
        f"Received audio processing request: {file.filename}, session: {session_id}, content_type: {file.content_type}"
    )

    # Validate and extract text from audio
    audio_bytes = await file.read()
    validate_audio_file(file.filename, len(audio_bytes))

    mime_type = file.content_type or "audio/ogg"
    transcribed_text = await transcribe_audio(audio_bytes, mime_type)

    logger.info(f"Audio transcription successful. Extracted {len(transcribed_text)} characters.")

    # Process through chat service
    message = transcribed_text
    chat_service = ChatService(db, client)
    response = await chat_service.process_message(message, session_id, platform)

    logger.info(f"Audio processed successfully. Session: {response.session_id}")

    return response
