"""OCR Service for extracting text from receipt images."""

from typing import Tuple

import cv2
import numpy as np
import pytesseract

from agent_api.core.decorators import handle_ocr_errors
from agent_api.core.exceptions import InvalidImageError, OCRProcessingError
from agent_api.core.logger import get_logger

logger = get_logger(__name__)

# Supported image formats
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
MAX_FILE_SIZE_MB = 10


def validate_image_file(filename: str, file_size: int) -> None:
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


@handle_ocr_errors
async def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Preprocess image for better OCR accuracy.

    Args:
        image_bytes: Raw image bytes

    Returns:
        Preprocessed image as numpy array
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise InvalidImageError("Failed to decode image. File may be corrupted.")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply binary thresholding with Otsu's method
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    return gray


@handle_ocr_errors
async def extract_text(image_bytes: bytes, lang: str = "eng") -> Tuple[str, float]:
    """Extract text from image using Tesseract OCR.

    Args:
        image_bytes: Raw image bytes
        lang: Language for OCR (default: 'eng' for English, use 'por' for Portuguese)

    Returns:
        Tuple of (extracted_text, confidence_score)

    Raises:
        OCRProcessingError: If OCR processing fails
        InvalidImageError: If image is invalid
    """
    logger.info(f"Starting OCR text extraction with language: {lang}")

    # Preprocess image
    processed_image = await preprocess_image(image_bytes)

    custom_config = r"--oem 3 --psm 3"
    text = pytesseract.image_to_string(processed_image, lang=lang, config=custom_config)

    data = pytesseract.image_to_data(
        processed_image,
        lang=lang,
        config=custom_config,
        output_type=pytesseract.Output.DICT,
    )

    confidences = [float(conf) for conf in data["conf"] if conf != "-1"]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    extracted_text = text.strip()

    if not extracted_text:
        raise OCRProcessingError(
            "No text could be extracted from the image. "
            "Please ensure the image is clear and contains readable text."
        )

    logger.info(
        f"OCR completed. Extracted {len(extracted_text)} characters "
        f"with {avg_confidence:.2f}% confidence"
    )

    return extracted_text, avg_confidence
