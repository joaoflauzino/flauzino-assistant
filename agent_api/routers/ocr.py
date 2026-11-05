"""OCR Router for receipt image processing."""

from typing import Any

from fastapi import APIRouter, File, Form, UploadFile

from agent_api.core.logger import get_logger
from agent_api.dependencies import ChatServiceDep, ReceiptServiceDep
from agent_api.schemas.dtos import ChatResponse
from agent_api.services.ocr import validate_image_file

logger = get_logger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/extract")
async def extract_text_from_image(
    service: ReceiptServiceDep,
    file: UploadFile = File(..., description="Receipt image file"),
) -> dict[str, Any]:
    """Extract text from an uploaded receipt image using OCR."""
    logger.info(f"Received OCR request for file: {file.filename}")

    image_bytes = await file.read()
    validate_image_file(file.filename, len(image_bytes))

    analysis = await service.analyze(image_bytes)

    return {
        "text": analysis.text,
        "confidence": round(analysis.confidence, 2),
        "char_count": len(analysis.text),
        "filename": file.filename,
    }


@router.post("/process-receipt", response_model=ChatResponse)
async def process_receipt_image(
    service: ReceiptServiceDep,
    chat_service: ChatServiceDep,
    file: UploadFile = File(..., description="Receipt image file"),
    session_id: str | None = Form(None, description="Chat session ID for context"),
    platform: str | None = Form(None, description="Platform originating the request"),
) -> ChatResponse:
    """Process a receipt image and start/continue a chat session."""
    logger.info(f"Received receipt processing request: {file.filename}, session: {session_id}")

    image_bytes = await file.read()
    validate_image_file(file.filename, len(image_bytes))

    analysis = await service.analyze(image_bytes)
    logger.info(
        f"OCR successful. Extracted {len(analysis.text)} characters "
        f"with {analysis.confidence:.2f}% confidence"
    )
    response = await chat_service.process_message(
        service.build_message(analysis),
        session_id,
        platform,
    )
    logger.info(f"Receipt processed successfully. Session: {response.session_id}")
    return response
