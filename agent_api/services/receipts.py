"""Receipt use case: OCR analysis plus the business instruction sent to chat.

Keeping the prompt here keeps the router as a thin HTTP boundary while
preserving the existing endpoint contracts.
"""

from agent_api.schemas.receipts import ReceiptAnalysis
from agent_api.services.ocr_protocols import OCRServiceProtocol


def build_receipt_prompt(extracted_text: str) -> str:
    """Builds the chat instruction that asks the agent to analyse a receipt."""
    return (
        f"O usuário enviou a foto de um recibo/comprovante. O texto extraído via OCR foi:\n\n"
        f"```\n{extracted_text}\n```\n\n"
        "Analise o texto do recibo e apresente IMEDIATAMENTE os dados identificados "
        "(valor total, local/estabelecimento, data, itens e método de pagamento se houver). "
        "Pergunte com clareza quais informações obrigatórias ainda faltam para registrar o gasto "
        "(categoria, item comprado, método de pagamento, local da compra). "
        "NUNCA responda apenas com frases intermediárias como 'vou organizar as informações'."
    )


class ReceiptService:
    """Extracts receipt data and builds the conversation instruction."""

    def __init__(self, ocr_service: OCRServiceProtocol) -> None:
        self._ocr_service = ocr_service

    async def analyze(self, image_bytes: bytes) -> ReceiptAnalysis:
        """Extracts the receipt text and confidence through the OCR contract."""
        text, confidence = await self._ocr_service.extract_text(image_bytes)
        return ReceiptAnalysis(text=text, confidence=confidence)

    def build_message(self, analysis: ReceiptAnalysis) -> str:
        """Builds the chat message that carries the OCR result to the agent."""
        return build_receipt_prompt(analysis.text)
