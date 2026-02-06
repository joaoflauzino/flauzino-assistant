"""Unit tests for OCR router endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO
from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager

from agent_api.main import app
from agent_api.schemas.dtos import ChatResponse, ChatMessage
from agent_api.core.exceptions import OCRProcessingError, InvalidImageError


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_client():
    """Fixture for test client."""
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client


@pytest.fixture
def sample_image_file():
    """Create a mock image file for upload."""
    file_content = b"fake image content"
    return BytesIO(file_content)


@pytest.fixture
def mock_ocr_service(mocker):
    """Mock OCR service."""
    service_patch = mocker.patch("agent_api.routers.ocr.ocr_service")
    # Make extract_text return an AsyncMock
    service_patch.extract_text = AsyncMock()
    return service_patch


@pytest.fixture
def mock_chat_service(mocker):
    """Mock ChatService."""
    MockService = mocker.patch("agent_api.routers.ocr.ChatService")
    instance = MockService.return_value
    instance.process_message = AsyncMock()
    return instance


class TestOCRExtractEndpoint:
    """Tests for POST /ocr/extract endpoint."""

    async def test_extract_text_success(self, test_client, mock_ocr_service):
        """Test successful text extraction from image."""
        # Arrange
        mock_ocr_service.extract_text.return_value = (
            "SUPERMERCADO XYZ\nTotal: R$ 50.00",
            85.5
        )

        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}

        # Act
        response = await test_client.post("/ocr/extract", files=files)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "SUPERMERCADO XYZ\nTotal: R$ 50.00"
        assert data["confidence"] == 85.5
        assert data["char_count"] == 32  # Length of the text above
        assert data["filename"] == "receipt.jpg"

    async def test_extract_text_invalid_file_type(self, test_client):
        """Test rejection of invalid file types."""
        # Arrange
        files = {"file": ("document.txt", b"some text", "text/plain")}

        # Act
        response = await test_client.post("/ocr/extract", files=files)

        # Assert
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    async def test_extract_text_no_text_extracted(
        self, test_client, mock_ocr_service
    ):
        """Test when no text can be extracted from image."""
        # Arrange
        from agent_api.core.exceptions import OCRProcessingError
        mock_ocr_service.extract_text.side_effect = OCRProcessingError(
            "No text could be extracted"
        )
        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}

        # Act
        response = await test_client.post("/ocr/extract", files=files)

        # Assert
        assert response.status_code == 400

    async def test_extract_text_handles_ocr_error(
        self, test_client, mock_ocr_service
    ):
        """Test error handling when OCR fails."""
        # Arrange
        from agent_api.core.exceptions import OCRProcessingError
        mock_ocr_service.extract_text.side_effect = OCRProcessingError("OCR failed")
        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}

        # Act
        response = await test_client.post("/ocr/extract", files=files)

        # Assert
        assert response.status_code == 400

    async def test_extract_text_supports_multiple_formats(
        self, test_client, mock_ocr_service
    ):
        """Test that various image formats are accepted."""
        # Arrange
        mock_ocr_service.extract_text.return_value = ("Text", 80.0)
        formats = [
            ("image.jpg", "image/jpeg"),
            ("image.png", "image/png"),
            ("image.webp", "image/webp"),
        ]

        for filename, mime_type in formats:
            # Act
            files = {"file": (filename, b"fake image", mime_type)}
            response = await test_client.post("/ocr/extract", files=files)

            # Assert
            assert response.status_code == 200, f"Failed for {filename}"


class TestOCRProcessReceiptEndpoint:
    """Tests for POST /ocr/process-receipt endpoint."""

    async def test_process_receipt_creates_new_session(
        self, test_client, mock_ocr_service, mock_chat_service
    ):
        """Test processing receipt creates new chat session."""
        # Arrange
        mock_ocr_service.extract_text.return_value = (
            "MERCADO\nTotal: 132,07",
            75.0
        )

        fake_session_id = "test-session-id-123"
        mock_chat_service.process_message.return_value = ChatResponse(
            response="Preciso do método de pagamento...",
            session_id=fake_session_id,
            history=[
                ChatMessage(
                    role="user",
                    content="Aqui está o texto extraído de um recibo..."
                ),
                ChatMessage(
                    role="assistant",
                    content="Preciso do método de pagamento..."
                )
            ]
        )

        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}

        # Act
        response = await test_client.post("/ocr/process-receipt", files=files)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == fake_session_id
        assert "Preciso do método de pagamento" in data["response"]
        assert len(data["history"]) == 2

        # Verify ChatService was called with OCR text
        mock_chat_service.process_message.assert_awaited_once()
        message_arg = mock_chat_service.process_message.call_args[0][0]
        assert "MERCADO" in message_arg
        assert "132,07" in message_arg

    async def test_process_receipt_continues_existing_session(
        self, test_client, mock_ocr_service, mock_chat_service
    ):
        """Test processing receipt with existing session_id."""
        # Arrange
        mock_ocr_service.extract_text.return_value = ("Receipt text", 80.0)

        existing_session = "existing-session-123"
        mock_chat_service.process_message.return_value = ChatResponse(
            response="Continuing...",
            session_id=existing_session,
            history=[]
        )

        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}
        data = {"session_id": existing_session}

        # Act
        response = await test_client.post(
            "/ocr/process-receipt",
            files=files,
            data=data
        )

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["session_id"] == existing_session

        # Verify session_id was passed to ChatService
        call_args = mock_chat_service.process_message.call_args[0]
        assert call_args[1] == existing_session

    async def test_process_receipt_no_text_extracted(
        self, test_client, mock_ocr_service
    ):
        """Test when OCR extracts no text from receipt."""
        # Arrange
        from agent_api.core.exceptions import OCRProcessingError
        mock_ocr_service.extract_text.side_effect = OCRProcessingError(
            "No text extracted"
        )
        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}

        # Act
        response = await test_client.post("/ocr/process-receipt", files=files)

        # Assert
        assert response.status_code == 400

    async def test_process_receipt_invalid_image(self, test_client):
        """Test rejection of invalid image files."""
        # Arrange
        files = {"file": ("document.pdf", b"fake pdf", "application/pdf")}

        # Act
        response = await test_client.post("/ocr/process-receipt", files=files)

        # Assert
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    async def test_process_receipt_handles_nonexistent_session(
        self, test_client, mock_ocr_service, mock_chat_service
    ):
        """Test handling of non-existent session ID."""
        # Arrange
        from fastapi import HTTPException
        mock_ocr_service.extract_text.return_value = ("Text", 80.0)
        mock_chat_service.process_message.side_effect = HTTPException(
            status_code=404, detail="Session not found"
        )

        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}
        data = {"session_id": "nonexistent-session"}

        # Act
        response = await test_client.post("/ocr/process-receipt", files=files, data=data)

        # Assert
        assert response.status_code == 404



class TestOCRValidation:
    """Tests for OCR validation logic."""

    async def test_validate_image_rejects_unsupported_extensions(
        self, test_client
    ):
        """Test that unsupported file extensions are rejected."""
        unsupported_files = [
            ("file.txt", "text/plain"),
            ("file.pdf", "application/pdf"),
            ("file.doc", "application/msword"),
        ]

        for filename, mime_type in unsupported_files:
            files = {"file": (filename, b"content", mime_type)}
            response = await test_client.post("/ocr/extract", files=files)
            assert response.status_code == 400

    async def test_validate_image_accepts_supported_extensions(
        self, test_client, mock_ocr_service
    ):
        """Test that supported image extensions are accepted."""
        # Arrange
        mock_ocr_service.extract_text.return_value = ("Text", 80.0)

        supported_files = [
            "image.jpg", "image.jpeg", "image.png",
            "image.webp", "image.bmp", "image.tiff"
        ]

        for filename in supported_files:
            files = {"file": (filename, b"fake image", "image/jpeg")}
            response = await test_client.post("/ocr/extract", files=files)
            assert response.status_code == 200, f"Failed for {filename}"
