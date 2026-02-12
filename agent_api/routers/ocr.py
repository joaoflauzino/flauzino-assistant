"""OCR Router for receipt image processing."""

import httpx
from fastapi import APIRouter, File, UploadFile, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from agent_api.core.database import get_db
from agent_api.core.http_client import get_http_client
from agent_api.core.logger import get_logger
from agent_api.services.ocr import ocr_service, OCRService
from agent_api.services.chat import ChatService
from agent_api.schemas.dtos import ChatResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/extract")
async def extract_text_from_image(
    file: UploadFile = File(..., description="Receipt image file"),
):
    """
    Extract text from an uploaded receipt image using OCR.

    Returns the extracted text and confidence score.
    """
    logger.info(f"Received OCR request for file: {file.filename}")

    # Validate file
    image_bytes = await file.read()
    OCRService.validate_image_file(file.filename, len(image_bytes))

    # Extract text using OCR
    text, confidence = await ocr_service.extract_text(image_bytes)

    return {
        "text": text,
        "confidence": round(confidence, 2),
        "char_count": len(text),
        "filename": file.filename,
    }


@router.post("/process-receipt", response_model=ChatResponse)
async def process_receipt_image(
    file: UploadFile = File(..., description="Receipt image file"),
    session_id: Optional[str] = Form(None, description="Chat session ID for context"),
    client: httpx.AsyncClient = Depends(get_http_client),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a receipt image and start/continue a chat session.

    This endpoint:
    1. Extracts text from the receipt image using OCR
    2. Creates or continues a chat session
    3. Processes the extracted text through the chat service
    4. Returns the assistant's response and session ID

    You can then continue the conversation using the /chat endpoint
    with the returned session_id to provide missing information.
    """
    logger.info(
        f"Received receipt processing request: {file.filename}, session: {session_id}"
    )

    # Validate and extract text from image
    image_bytes = await file.read()
    OCRService.validate_image_file(file.filename, len(image_bytes))

    extracted_text, confidence = await ocr_service.extract_text(image_bytes)

    logger.info(
        f"OCR successful. Extracted {len(extracted_text)} characters "
        f"with {confidence:.2f}% confidence"
    )

    # Process through chat service
    message = (
        f"Aqui está o texto extraído de um recibo/nota fiscal:\n\n"
        f"{extracted_text}\n\n"
        f"Por favor, extraia as informações de gastos."
    )

    # Use ChatService to handle session and LLM processing
    chat_service = ChatService(db, client)
    response = await chat_service.process_message(message, session_id)

    logger.info(f"Receipt processed successfully. Session: {response.session_id}")

    return response
