from unittest.mock import MagicMock, patch

import pytest

from agent_api.core.exceptions import AudioProcessingError, InvalidAudioError
from agent_api.services.audio import (
    MAX_AUDIO_SIZE_BYTES,
    transcribe_audio,
    validate_audio_file,
)


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
