"""Structural contracts for image preprocessing and text recognition."""

from typing import Protocol

import numpy as np


class ImagePreprocessor(Protocol):
    """Synchronous image preprocessing backend (run off the event loop)."""

    def preprocess(self, image_bytes: bytes) -> np.ndarray: ...


class TextRecognizer(Protocol):
    """Synchronous text recognition backend (run off the event loop)."""

    def recognize(self, image: np.ndarray, lang: str) -> tuple[str, float]: ...


class OCRServiceProtocol(Protocol):
    """Async façade consumed by the OCR router and receipt use case."""

    async def preprocess_image(self, image_bytes: bytes) -> np.ndarray: ...

    async def extract_text(self, image_bytes: bytes, lang: str = "eng") -> tuple[str, float]: ...
