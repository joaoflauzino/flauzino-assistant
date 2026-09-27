"""OCR Router for receipt image processing."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from agent_api.core.logger import get_logger
from agent_api.dependencies import get_chat_service
from agent_api.schemas.dtos import ChatResponse
from agent_api.services.chat import ChatService
from agent_api.services.ocr import extract_text, validate_image_file

logger = get_logger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/extract")
async def extract_text_from_image(
    file: UploadFile = File(..., description="Receipt image file"),
):
    """Extract text from an uploaded receipt image using OCR."""
    logger.info(f"Received OCR request for file: {file.filename}")

    # Validate file
    image_bytes = await file.read()
    validate_image_file(file.filename, len(image_bytes))

    # Extract text using OCR
    text, confidence = await extract_text(image_bytes)

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
    platform: Optional[str] = Form(None, description="Platform originating the request"),
    service: ChatService = Depends(get_chat_service),
):
    """Process a receipt image and start/continue a chat session."""
    logger.info(f"Received receipt processing request: {file.filename}, session: {session_id}")

    # Validate and extract text from image
    image_bytes = await file.read()
    validate_image_file(file.filename, len(image_bytes))

    extracted_text, confidence = await extract_text(image_bytes)

    logger.info(
        f"OCR successful. Extracted {len(extracted_text)} characters "
        f"with {confidence:.2f}% confidence"
    )

    # Process through chat service with direct and unambiguous instructions
    message = (
        f"O usuário enviou a foto de um recibo/comprovante. O texto extraído via OCR foi:\n\n"
        f"```\n{extracted_text}\n```\n\n"
        "Analise o texto do recibo e apresente IMEDIATAMENTE os dados identificados "
        "(valor total, local/estabelecimento, data, itens e método de pagamento se houver). "
        "Pergunte com clareza quais informações obrigatórias ainda faltam para registrar o gasto "
        "(categoria, item comprado, método de pagamento, local da compra). "
        "NUNCA responda apenas com frases intermediárias como 'vou organizar as informações'."
    )

    response = await service.process_message(message, session_id, platform)

    logger.info(f"Receipt processed successfully. Session: {response.session_id}")

    return response
