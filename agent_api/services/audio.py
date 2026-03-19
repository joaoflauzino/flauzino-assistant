import tempfile
import os
from faster_whisper import WhisperModel

from agent_api.core.logger import get_logger

logger = get_logger(__name__)


class AudioService:
    @staticmethod
    def validate_audio_file(filename: str, file_size: int) -> None:
        """Validate audio file extension and size."""
        # Check size (e.g., max 10MB)
        if file_size > 10 * 1024 * 1024:
            from agent_api.core.exceptions import InvalidAudioError
            raise InvalidAudioError(f"Arquivo de áudio muito grande: {file_size} bytes. Máximo permitido é 10MB.")

    @staticmethod
    async def transcribe_audio(audio_bytes: bytes, mime_type: str) -> str:
        """Transcribe audio using faster-whisper locally."""
        try:
            logger.info(f"Writing audio ({len(audio_bytes)} bytes) to temporary file for Whisper transcription.")
            
            # Write audio to a temporary file for faster-whisper to read
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name

            logger.info("Initializing Faster Whisper model...")
            # Using int8 for CPU, assuming running on Raspberry Pi or similar light environments
            model = WhisperModel("base", device="cpu", compute_type="int8")

            logger.info("Transcribing audio...")
            segments, info = model.transcribe(
                tmp_file_path,
                beam_size=5,
                language="pt",
                vad_filter=True
            )

            # Combine all transcribed segments
            transcribed_text = " ".join([segment.text for segment in segments]).strip()
            
            logger.info(f"Transcription successful. Detected language: {info.language}")
            
            # Clean up the temp file
            os.remove(tmp_file_path)
            
            return transcribed_text
            
        except Exception as e:
            logger.error(f"Error transcribing audio with Whisper: {e}", exc_info=True)
            from agent_api.core.exceptions import AudioProcessingError
            raise AudioProcessingError(f"Falha ao transcrever o áudio: {str(e)}")


audio_service = AudioService()
