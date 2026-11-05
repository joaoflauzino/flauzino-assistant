"""Audio transcription with a sync adapter kept outside the event loop."""

import asyncio
import os
import tempfile
from collections.abc import Callable

from faster_whisper import WhisperModel

from agent_api.core.decorators import handle_audio_errors
from agent_api.core.exceptions import InvalidAudioError
from agent_api.core.logger import get_logger
from agent_api.services.audio_protocols import AudioTranscriber

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


def validate_audio_file(filename: str | None, file_size: int) -> None:
    """Validate audio file extension and size."""
    if file_size > MAX_AUDIO_SIZE_BYTES:
        raise InvalidAudioError(
            f"Arquivo de áudio muito grande: {file_size} bytes. Máximo permitido é 10MB."
        )


class FasterWhisperTranscriber:
    """Sync Faster-Whisper adapter, including the temporary file lifecycle."""

    def __init__(self, model_factory: Callable[[], WhisperModel] | None = None) -> None:
        self._model_factory = model_factory or get_model

    def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribes audio bytes, always removing the temporary file."""
        tmp_file_path: str | None = None
        try:
            logger.info(
                f"Writing audio ({len(audio_bytes)} bytes) to temporary file "
                "for Whisper transcription."
            )
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name

            model = self._model_factory()
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


class AudioService:
    """Async boundary that runs the blocking transcriber in a worker thread."""

    def __init__(self, transcriber: AudioTranscriber) -> None:
        self._transcriber = transcriber

    @handle_audio_errors
    async def transcribe(self, audio_bytes: bytes) -> str:
        return await asyncio.to_thread(self._transcriber.transcribe, audio_bytes)


def build_default_audio_service() -> AudioService:
    """Composes the default audio service for providers and legacy callers."""
    return AudioService(FasterWhisperTranscriber())


async def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """Backward-compatible function that delegates to the default service."""
    return await build_default_audio_service().transcribe(audio_bytes)
