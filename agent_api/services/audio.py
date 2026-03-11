import base64
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from agent_api.core.logger import get_logger
from agent_api.settings import settings

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
        """Transcribe audio using Gemini."""
        try:
            llm = ChatGoogleGenerativeAI(
                model=settings.AUDIO_MODEL_NAME, 
                temperature=0
            )
            
            audio_data = base64.b64encode(audio_bytes).decode("utf-8")
            
            message = HumanMessage(
                content=[
                    {
                        "type": "text", 
                        "text": "Por favor, transcreva o áudio a seguir exatamente como foi falado, sem adicionar nenhum outro comentário ou texto."
                    },
                    {
                        "type": "media",
                        "mime_type": mime_type,
                        "data": audio_data
                    }
                ]
            )
            
            logger.info(f"Calling Gemini to transcribe audio of length {len(audio_bytes)} bytes")
            response = await llm.ainvoke([message])
            return response.content
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            from agent_api.core.exceptions import AudioProcessingError
            raise AudioProcessingError(f"Falha ao transcrever o áudio: {str(e)}")


audio_service = AudioService()
