"""Audio Router for processing voice messages and audio files."""

from fastapi import APIRouter, File, Form, UploadFile

from agent_api.core.logger import get_logger
from agent_api.dependencies import AudioServiceDep, ChatServiceDep
from agent_api.schemas.dtos import ChatResponse
from agent_api.services.audio import validate_audio_file

logger = get_logger(__name__)

router = APIRouter(prefix="/audio", tags=["Audio"])


@router.post("/process-audio", response_model=ChatResponse)
async def process_audio_file(
    audio_service: AudioServiceDep,
    service: ChatServiceDep,
    file: UploadFile = File(..., description="Audio file"),
    session_id: str | None = Form(None, description="Chat session ID for context"),
    platform: str | None = Form(None, description="Platform originating the request"),
) -> ChatResponse:
    """Process an audio file and start/continue a chat session."""
    logger.info(
        f"Received audio processing request: {file.filename}, session: {session_id}, content_type: {file.content_type}"
    )

    audio_bytes = await file.read()
    validate_audio_file(file.filename, len(audio_bytes))

    transcribed_text = await audio_service.transcribe(audio_bytes)

    logger.info(f"Audio transcription successful. Extracted {len(transcribed_text)} characters.")

    response = await service.process_message(transcribed_text, session_id, platform)

    logger.info(f"Audio processed successfully. Session: {response.session_id}")

    return response
