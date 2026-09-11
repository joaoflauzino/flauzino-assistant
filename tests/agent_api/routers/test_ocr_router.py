"""Unit tests for OCR router endpoints."""

from io import BytesIO
from unittest.mock import AsyncMock

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
import pytest

from agent_api.core.exceptions import OCRProcessingError
from agent_api.main import app
from agent_api.schemas.dtos import ChatMessage, ChatResponse

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
    """Mock OCR extract_text function."""
    mock_extract = mocker.patch("agent_api.routers.ocr.extract_text", new_callable=AsyncMock)
    mock_holder = mocker.MagicMock()
    mock_holder.extract_text = mock_extract
    return mock_holder


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
            85.5,
        )

        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}

        # Act
        response = await test_client.post("/ocr/extract", files=files)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "SUPERMERCADO XYZ\nTotal: R$ 50.00"
        assert data["confidence"] == 85.5
        assert data["filename"] == "receipt.jpg"
        assert data["char_count"] == len(data["text"])

    async def test_extract_text_missing_file(self, test_client):
        """Test error when no file is provided."""
        # Act
        response = await test_client.post("/ocr/extract")

        # Assert
        assert response.status_code == 422  # Validation error

    async def test_extract_text_invalid_file_extension(self, test_client):
        """Test error with invalid file extension."""
        # Arrange
        files = {"file": ("document.pdf", b"fake pdf", "application/pdf")}

        # Act
        response = await test_client.post("/ocr/extract", files=files)

        # Assert
        assert response.status_code == 400

    async def test_extract_text_no_text_extracted(self, test_client, mock_ocr_service):
        """Test handling when OCR finds no text."""
        # Arrange
        mock_ocr_service.extract_text.side_effect = OCRProcessingError(
            "No text could be extracted"
        )

        files = {"file": ("blank.jpg", b"fake blank image", "image/jpeg")}

        # Act
        response = await test_client.post("/ocr/extract", files=files)

        # Assert
        assert response.status_code == 400

    async def test_extract_text_handles_ocr_error(self, test_client, mock_ocr_service):
        """Test handling of OCR processing errors."""
        # Arrange
        mock_ocr_service.extract_text.side_effect = OCRProcessingError("OCR failed")

        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}

        # Act
        response = await test_client.post("/ocr/extract", files=files)

        # Assert
        assert response.status_code == 400

    async def test_extract_text_supports_multiple_formats(
        self, test_client, mock_ocr_service
    ):
        """Test that multiple image formats are supported."""
        formats = [
            ("receipt.png", "image/png"),
            ("receipt.webp", "image/webp"),
            ("receipt.bmp", "image/bmp"),
        ]

        mock_ocr_service.extract_text.return_value = ("Text", 80.0)

        for filename, mime_type in formats:
            files = {"file": (filename, b"fake image", mime_type)}
            response = await test_client.post("/ocr/extract", files=files)
            assert response.status_code == 200


class TestOCRProcessReceiptEndpoint:
    """Tests for POST /ocr/process-receipt endpoint."""

    async def test_process_receipt_new_session_success(
        self, test_client, mock_ocr_service, mock_chat_service
    ):
        """Test successful receipt processing creating a new session."""
        # Arrange
        mock_ocr_service.extract_text.return_value = ("MERCADO\nTotal: 132,07", 75.0)

        expected_response = ChatResponse(
            response="Extraí os dados: Mercado R$ 132,07. Confirma?",
            session_id="new-session-id",
            history=[ChatMessage(role="assistant", content="Response")],
            is_complete=False,
            suggested_options=["Sim", "Não"],
        )
        mock_chat_service.process_message.return_value = expected_response

        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}

        # Act
        response = await test_client.post("/ocr/process-receipt", files=files)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "new-session-id"
        assert data["response"] == "Extraí os dados: Mercado R$ 132,07. Confirma?"

        # Verify chat service was called with formatted message
        mock_chat_service.process_message.assert_called_once()
        call_args = mock_chat_service.process_message.call_args[0]
        assert "MERCADO" in call_args[0]
        assert "132,07" in call_args[0]
        assert call_args[1] is None  # session_id should be None

    async def test_process_receipt_existing_session_success(
        self, test_client, mock_ocr_service, mock_chat_service
    ):
        """Test receipt processing with existing session ID."""
        # Arrange
        existing_session_id = "existing-uuid-1234"
        mock_ocr_service.extract_text.return_value = ("Receipt text", 80.0)

        expected_response = ChatResponse(
            response="Gasto adicionado à sessão existente.",
            session_id=existing_session_id,
            history=[],
            is_complete=False,
        )
        mock_chat_service.process_message.return_value = expected_response

        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}
        data = {"session_id": existing_session_id}

        # Act
        response = await test_client.post(
            "/ocr/process-receipt", files=files, data=data
        )

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["session_id"] == existing_session_id

        # Verify session_id was passed to chat service
        mock_chat_service.process_message.assert_called_once()
        call_args = mock_chat_service.process_message.call_args[0]
        assert call_args[1] == existing_session_id

    async def test_process_receipt_no_text_extracted(
        self, test_client, mock_ocr_service
    ):
        """Test handling when receipt has no readable text."""
        # Arrange
        mock_ocr_service.extract_text.side_effect = OCRProcessingError(
            "No text extracted"
        )

        files = {"file": ("blank.jpg", b"fake image", "image/jpeg")}

        # Act
        response = await test_client.post("/ocr/process-receipt", files=files)

        # Assert
        assert response.status_code == 400

    async def test_process_receipt_with_platform_param(
        self, test_client, mock_ocr_service, mock_chat_service
    ):
        """Test receipt processing with platform parameter."""
        # Arrange
        expected_response = ChatResponse(
            response="Resposta formatada para Telegram",
            session_id="session-id",
            history=[],
            is_complete=False,
        )
        mock_chat_service.process_message.return_value = expected_response
        mock_ocr_service.extract_text.return_value = ("Text", 80.0)

        files = {"file": ("receipt.jpg", b"fake image", "image/jpeg")}
        data = {"platform": "telegram"}

        # Act
        response = await test_client.post(
            "/ocr/process-receipt", files=files, data=data
        )

        # Assert
        assert response.status_code == 200

        # Verify platform was passed to chat service
        mock_chat_service.process_message.assert_called_once()
        call_args = mock_chat_service.process_message.call_args[0]
        assert call_args[2] == "telegram"  # platform parameter


class TestOCRValidation:
    """Tests for OCR validation logic."""

    async def test_validate_image_rejects_unsupported_extensions(self, test_client):
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
            "image.jpg",
            "image.jpeg",
            "image.png",
            "image.webp",
            "image.bmp",
            "image.tiff",
        ]

        for filename in supported_files:
            files = {"file": (filename, b"image data", "image/jpeg")}
            response = await test_client.post("/ocr/extract", files=files)
            assert response.status_code == 200
