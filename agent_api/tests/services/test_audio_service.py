import threading
from unittest.mock import MagicMock, patch

import pytest

from agent_api.core.exceptions import AudioProcessingError, InvalidAudioError
from agent_api.dependencies import get_audio_service
from agent_api.services.audio import (
    MAX_AUDIO_SIZE_BYTES,
    AudioService,
    FasterWhisperTranscriber,
    transcribe_audio,
    validate_audio_file,
)


class StubTranscriber:
    def __init__(self, text: str = "texto", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls = 0
        self.thread_ident: int | None = None

    def transcribe(self, audio_bytes: bytes) -> str:
        self.calls += 1
        self.thread_ident = threading.get_ident()
        if self.error is not None:
            raise self.error
        return self.text


def test_validate_audio_file_valid():
    # Should not raise
    validate_audio_file("voice.ogg", 1024)


def test_validate_audio_file_exceeds_size():
    with pytest.raises(InvalidAudioError) as exc:
        validate_audio_file("large.ogg", MAX_AUDIO_SIZE_BYTES + 1)
    assert "Arquivo de áudio muito grande" in str(exc.value)


@pytest.mark.asyncio
async def test_transcribe_audio_success():
    fake_segment = MagicMock()
    fake_segment.text = "Gastei dez reais no mercado"
    fake_info = MagicMock()
    fake_info.language = "pt"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([fake_segment], fake_info)

    with patch("agent_api.services.audio.get_model", return_value=mock_model):
        with patch("os.remove") as mock_remove:
            result = await transcribe_audio(b"dummy audio bytes")
            assert result == "Gastei dez reais no mercado"
            mock_remove.assert_called_once()


@pytest.mark.asyncio
async def test_transcribe_audio_cleanup_on_error():
    mock_model = MagicMock()
    mock_model.transcribe.side_effect = RuntimeError("Whisper crashed")

    with patch("agent_api.services.audio.get_model", return_value=mock_model):
        with patch("os.remove") as mock_remove:
            with pytest.raises(AudioProcessingError) as exc:
                await transcribe_audio(b"dummy audio bytes")
            assert "Falha ao transcrever o áudio" in str(exc.value)
            mock_remove.assert_called_once()


@pytest.mark.asyncio
async def test_audio_service_offloads_transcriber_to_worker_thread():
    transcriber = StubTranscriber("Gastei dez reais")
    service = AudioService(transcriber)

    result = await service.transcribe(b"audio")

    assert result == "Gastei dez reais"
    assert transcriber.calls == 1
    assert transcriber.thread_ident is not None
    assert transcriber.thread_ident != threading.get_ident()


@pytest.mark.asyncio
async def test_audio_service_translates_adapter_failure():
    service = AudioService(StubTranscriber(error=RuntimeError("backend down")))

    with pytest.raises(AudioProcessingError, match="Falha ao transcrever o áudio"):
        await service.transcribe(b"audio")


def test_faster_whisper_transcriber_uses_injected_model_factory():
    model = MagicMock()
    segment = MagicMock(text="texto")
    model.transcribe.return_value = ([segment], MagicMock(language="pt"))
    factory = MagicMock(return_value=model)
    transcriber = FasterWhisperTranscriber(model_factory=factory)

    with patch("os.remove"):
        result = transcriber.transcribe(b"audio")

    assert result == "texto"
    factory.assert_called_once_with()
    model.transcribe.assert_called_once()


def test_faster_whisper_transcriber_tolerates_cleanup_failure():
    model = MagicMock()
    segment = MagicMock(text="texto")
    model.transcribe.return_value = ([segment], MagicMock(language="pt"))
    transcriber = FasterWhisperTranscriber(model_factory=MagicMock(return_value=model))

    with patch("os.path.exists", return_value=True):
        with patch("os.remove", side_effect=OSError("locked")):
            result = transcriber.transcribe(b"audio")

    assert result == "texto"


def test_get_audio_service_builds_default_composition():
    service = get_audio_service()

    assert isinstance(service, AudioService)
    assert isinstance(service._transcriber, FasterWhisperTranscriber)
