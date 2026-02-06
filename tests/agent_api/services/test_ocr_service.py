"""Unit tests for OCR service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
from PIL import Image
import io

from agent_api.services.ocr import OCRService
from agent_api.core.exceptions import InvalidImageError, OCRProcessingError


@pytest.fixture
def sample_image_bytes():
    """Create a simple test image as bytes."""
    # Create a simple white image with black text-like shapes
    img = Image.new('RGB', (200, 100), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.read()


@pytest.fixture
def corrupted_image_bytes():
    """Create corrupted image data."""
    return b"not a valid image"


class TestOCRService:
    """Test suite for OCR Service."""

    @pytest.mark.asyncio
    async def test_preprocess_image_converts_to_grayscale(self, sample_image_bytes):
        """Test that preprocessing converts image to grayscale binary."""
        # Act
        result = await OCRService.preprocess_image(sample_image_bytes)

        # Assert
        assert isinstance(result, np.ndarray)
        assert len(result.shape) == 2  # Should be 2D (grayscale)

    @pytest.mark.asyncio
    async def test_preprocess_image_applies_thresholding(self, sample_image_bytes):
        """Test that binary thresholding is applied."""
        # Act
        result = await OCRService.preprocess_image(sample_image_bytes)

        # Assert
        # Binary image should only have 0 and 255 values
        unique_values = np.unique(result)
        assert all(v in [0, 255] for v in unique_values)

    @pytest.mark.asyncio
    async def test_preprocess_image_handles_invalid_data(self, corrupted_image_bytes):
        """Test that preprocessing raises error for invalid image data."""
        # Act & Assert
        with pytest.raises((InvalidImageError, OCRProcessingError)):
            await OCRService.preprocess_image(corrupted_image_bytes)

    def test_validate_image_file_rejects_invalid_extensions(self):
        """Test validation rejects invalid file extensions."""
        # Act & Assert
        with pytest.raises(InvalidImageError):
            OCRService.validate_image_file("file.txt", 1000)

    def test_validate_image_file_rejects_large_files(self):
        """Test validation rejects files that are too large."""
        # 11 MB file
        large_file_size = 11 * 1024 * 1024
        
        # Act & Assert
        with pytest.raises(InvalidImageError):
            OCRService.validate_image_file("file.jpg", large_file_size)

    def test_validate_image_file_accepts_valid_files(self):
        """Test validation accepts valid files."""
        # Act - should not raise
        OCRService.validate_image_file("receipt.jpg", 1000)
        OCRService.validate_image_file("image.png", 500000)

    @pytest.mark.asyncio
    @patch('agent_api.services.ocr.pytesseract.image_to_string')
    @patch('agent_api.services.ocr.pytesseract.image_to_data')
    async def test_extract_text_returns_text_and_confidence(
        self, mock_image_to_data, mock_image_to_string, sample_image_bytes
    ):
        """Test that extract_text returns both text and confidence."""
        # Arrange
        mock_image_to_string.return_value = "Sample Receipt Text"
        mock_image_to_data.return_value = {
            'conf': ['75.5', '80.0', '90.5']
        }

        # Act
        text, confidence = await OCRService.extract_text(sample_image_bytes)

        # Assert
        assert text == "Sample Receipt Text"
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 100

    @pytest.mark.asyncio
    @patch('agent_api.services.ocr.pytesseract.image_to_string')
    @patch('agent_api.services.ocr.pytesseract.image_to_data')
    async def test_extract_text_calculates_average_confidence(
        self, mock_image_to_data, mock_image_to_string, sample_image_bytes
    ):
        """Test confidence score calculation."""
        # Arrange
        mock_image_to_string.return_value = "Text"
        mock_image_to_data.return_value = {
            'conf': ['80', '90', '70']  # Average should be 80
        }

        # Act
        _, confidence = await OCRService.extract_text(sample_image_bytes)

        # Assert
        assert confidence == 80.0

    @pytest.mark.asyncio
    @patch('agent_api.services.ocr.pytesseract.image_to_string')
    @patch('agent_api.services.ocr.pytesseract.image_to_data')
    async def test_extract_text_ignores_invalid_confidence_values(
        self, mock_image_to_data, mock_image_to_string, sample_image_bytes
    ):
        """Test that -1 confidence values are ignored."""
        # Arrange
        mock_image_to_string.return_value = "Text"
        mock_image_to_data.return_value = {
            'conf': ['80', '-1', '60']  # Should only average 80 and 60
        }

        # Act
        _, confidence = await OCRService.extract_text(sample_image_bytes)

        # Assert
        assert confidence == 70.0  # (80 + 60) / 2

    @pytest.mark.asyncio
    @patch('agent_api.services.ocr.pytesseract.image_to_string')
    @patch('agent_api.services.ocr.pytesseract.image_to_data')
    async def test_extract_text_uses_correct_language(
        self, mock_image_to_data, mock_image_to_string, sample_image_bytes
    ):
        """Test that language parameter is passed to Tesseract."""
        # Arrange
        mock_image_to_string.return_value = "Text"
        mock_image_to_data.return_value = {'conf': ['80']}

        # Act
        await OCRService.extract_text(sample_image_bytes, lang='por')

        # Assert
        mock_image_to_string.assert_called_once()
        call_kwargs = mock_image_to_string.call_args[1]
        assert call_kwargs['lang'] == 'por'

    @pytest.mark.asyncio
    @patch('agent_api.services.ocr.pytesseract.image_to_string')
    @patch('agent_api.services.ocr.pytesseract.image_to_data')
    async def test_extract_text_strips_whitespace(
        self, mock_image_to_data, mock_image_to_string, sample_image_bytes
    ):
        """Test that extracted text has whitespace stripped."""
        # Arrange
        mock_image_to_string.return_value = "  \n  Text with spaces  \n  "
        mock_image_to_data.return_value = {'conf': ['80']}

        # Act
        text, _ = await OCRService.extract_text(sample_image_bytes)

        # Assert
        assert text == "Text with spaces"

    @pytest.mark.asyncio
    @patch('agent_api.services.ocr.pytesseract.image_to_string')
    @patch('agent_api.services.ocr.pytesseract.image_to_data')
    async def test_extract_text_raises_on_empty_text(
        self, mock_image_to_data, mock_image_to_string, sample_image_bytes
    ):
        """Test error when no text is extracted."""
        # Arrange
        mock_image_to_string.return_value = "   "  # Only whitespace
        mock_image_to_data.return_value = {'conf': ['80']}

        # Act & Assert
        with pytest.raises(OCRProcessingError):
            await OCRService.extract_text(sample_image_bytes)

    @pytest.mark.asyncio
    @patch('agent_api.services.ocr.pytesseract.image_to_string')
    @patch('agent_api.services.ocr.pytesseract.image_to_data')
    async def test_extract_text_handles_empty_confidence_list(
        self, mock_image_to_data, mock_image_to_string, sample_image_bytes
    ):
        """Test handling when no confidence values are available."""
        # Arrange
        mock_image_to_string.return_value = "Text"
        mock_image_to_data.return_value = {'conf': []}

        # Act
        _, confidence = await OCRService.extract_text(sample_image_bytes)

        # Assert
        assert confidence == 0.0

