import os
import tempfile
from faster_whisper import WhisperModel

from agent_api.core.decorators import handle_audio_errors
from agent_api.core.exceptions import InvalidAudioError
from agent_api.core.logger import get_logger

logger = get_logger(__name__)

MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    """Lazy loader for Whisper model to avoid reloading weights on every request."""
    global _model
    if _model is None:
        logger.info("Initializing Faster Whisper model (singleton/lazy-load)...")
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def validate_audio_file(filename: str, file_size: int) -> None:
    """Validate audio file extension and size."""
    if file_size > MAX_AUDIO_SIZE_BYTES:
        raise InvalidAudioError(
            f"Arquivo de áudio muito grande: {file_size} bytes. Máximo permitido é 10MB."
        )


@handle_audio_errors
async def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """Transcribe audio using faster-whisper locally with guaranteed file cleanup."""
    tmp_file_path = None
    try:
        logger.info(
            f"Writing audio ({len(audio_bytes)} bytes) to temporary file for Whisper transcription."
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file_path = tmp_file.name

        model = get_model()

        logger.info("Transcribing audio...")
        segments, info = model.transcribe(
            tmp_file_path, beam_size=5, language="pt", vad_filter=True
        )

        transcribed_text = " ".join([segment.text for segment in segments]).strip()
        logger.info(f"Transcription successful. Detected language: {info.language}")
        return transcribed_text
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.remove(tmp_file_path)
            except OSError as err:
                logger.warning(f"Failed to remove temporary audio file {tmp_file_path}: {err}")
