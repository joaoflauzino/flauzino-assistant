"""Structural contracts for audio transcription."""

from typing import Protocol


class AudioTranscriber(Protocol):
    """Synchronous transcription backend (expected to run off the event loop)."""

    def transcribe(self, audio_bytes: bytes) -> str: ...


class AudioServiceProtocol(Protocol):
    """Async façade consumed by the routers and chat use cases."""

    async def transcribe(self, audio_bytes: bytes) -> str: ...
