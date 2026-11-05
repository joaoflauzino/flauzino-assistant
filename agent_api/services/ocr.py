"""OCR service for extracting text from receipt images.

OpenCV and Tesseract are CPU-bound and synchronous; they live behind the
``ImagePreprocessor``/``TextRecognizer`` adapters and are executed in a worker
thread so the async endpoints never block the event loop.
"""

import asyncio

import cv2
import numpy as np
import pytesseract

from agent_api.core.decorators import handle_ocr_errors
from agent_api.core.exceptions import InvalidImageError, OCRProcessingError
from agent_api.core.logger import get_logger
from agent_api.services.ocr_protocols import ImagePreprocessor, TextRecognizer
from agent_api.services.utils import average_confidence, clean_extracted_text

logger = get_logger(__name__)

# Supported image formats
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
MAX_FILE_SIZE_MB = 10
TESSERACT_CONFIG = r"--oem 3 --psm 3"


def validate_image_file(filename: str | None, file_size: int) -> None:
    """Validate image file format and size.

    Args:
        filename: Name of the uploaded file
        file_size: Size of the file in bytes

    Raises:
        InvalidImageError: If file type or size is invalid
    """
    if filename:
        ext = "." + filename.split(".")[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise InvalidImageError(f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise InvalidImageError(f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB")


class OpenCVImagePreprocessor:
    """Decodes and binarizes the image using OpenCV."""

    def preprocess(self, image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise InvalidImageError("Failed to decode image. File may be corrupted.")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]


class TesseractTextRecognizer:
    """Runs Tesseract over a preprocessed image."""

    def recognize(self, image: np.ndarray, lang: str) -> tuple[str, float]:
        text = pytesseract.image_to_string(image, lang=lang, config=TESSERACT_CONFIG)
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            config=TESSERACT_CONFIG,
            output_type=pytesseract.Output.DICT,
        )
        return text, average_confidence(data["conf"])


class OCRService:
    """Async OCR boundary that offloads the blocking adapters to a thread."""

    def __init__(
        self,
        preprocessor: ImagePreprocessor,
        recognizer: TextRecognizer,
    ) -> None:
        self._preprocessor = preprocessor
        self._recognizer = recognizer

    @handle_ocr_errors
    async def preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        """Preprocess the image for better OCR accuracy."""
        return await asyncio.to_thread(self._preprocessor.preprocess, image_bytes)

    @handle_ocr_errors
    async def extract_text(self, image_bytes: bytes, lang: str = "eng") -> tuple[str, float]:
        """Extract text from an image using Tesseract OCR."""
        logger.info(f"Starting OCR text extraction with language: {lang}")

        processed_image = await asyncio.to_thread(self._preprocessor.preprocess, image_bytes)
        raw_text, confidence = await asyncio.to_thread(
            self._recognizer.recognize, processed_image, lang
        )
        extracted_text = clean_extracted_text(raw_text)

        if not extracted_text:
            raise OCRProcessingError(
                "No text could be extracted from the image. "
                "Please ensure the image is clear and contains readable text."
            )

        logger.info(
            f"OCR completed. Extracted {len(extracted_text)} characters "
            f"with {confidence:.2f}% confidence"
        )
        return extracted_text, confidence


def build_default_ocr_service() -> OCRService:
    """Composes the default OCR service for providers and legacy callers."""
    return OCRService(
        preprocessor=OpenCVImagePreprocessor(),
        recognizer=TesseractTextRecognizer(),
    )


async def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Backward-compatible function that delegates to the default service."""
    return await build_default_ocr_service().preprocess_image(image_bytes)


async def extract_text(image_bytes: bytes, lang: str = "eng") -> tuple[str, float]:
    """Backward-compatible function that delegates to the default service."""
    return await build_default_ocr_service().extract_text(image_bytes, lang)
