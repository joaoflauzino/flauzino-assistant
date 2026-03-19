"""Audio Router for processing voice messages and audio files."""

import httpx
from fastapi import APIRouter, File, UploadFile, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from agent_api.core.database import get_db
from agent_api.core.http_client import get_http_client
from agent_api.core.logger import get_logger
from agent_api.services.audio import audio_service, AudioService
from agent_api.services.chat import ChatService
from agent_api.schemas.dtos import ChatResponse

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
    """
    Process an audio file and start/continue a chat session.

    This endpoint:
    1. Transcribes the audio using faster-whisper locally
    2. Creates or continues a chat session
    3. Processes the transcribed text through the chat service
    4. Returns the assistant's response and session ID
    """
    logger.info(
        f"Received audio processing request: {file.filename}, session: {session_id}, content_type: {file.content_type}"
    )

    # Validate and extract text from audio
    audio_bytes = await file.read()
    AudioService.validate_audio_file(file.filename, len(audio_bytes))

    mime_type = file.content_type or "audio/ogg"
    
    transcribed_text = await audio_service.transcribe_audio(audio_bytes, mime_type)

    logger.info(
        f"Audio transcription successful. Extracted {len(transcribed_text)} characters."
    )

    # Process through chat service
    # We pass the transcibed text naturally, mimicking text input from the user
    message = transcribed_text

    # Use ChatService to handle session and LLM processing
    chat_service = ChatService(db, client)
    response = await chat_service.process_message(message, session_id, platform)

    logger.info(f"Audio processed successfully. Session: {response.session_id}")

    return response
