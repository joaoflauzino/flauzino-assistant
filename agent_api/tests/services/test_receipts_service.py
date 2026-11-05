from unittest.mock import AsyncMock

import pytest

from agent_api.services.ocr import OCRService
from agent_api.services.receipts import ReceiptService, build_receipt_prompt


@pytest.fixture
def mock_ocr_service():
    service = AsyncMock(spec=OCRService)
    service.extract_text.return_value = ("MERCADO XYZ\nTotal: R$ 132,07", 88.5)
    return service


@pytest.fixture
def receipt_service(mock_ocr_service):
    return ReceiptService(ocr_service=mock_ocr_service)


def test_receipt_prompt_includes_extracted_text_and_required_fields():
    prompt = build_receipt_prompt("MERCADO XYZ\nTotal: 132,07")

    assert "MERCADO XYZ" in prompt
    assert "132,07" in prompt
    assert "categoria" in prompt
    assert "item comprado" in prompt
    assert "método de pagamento" in prompt
    assert "local da compra" in prompt


@pytest.mark.asyncio
async def test_analyze_delegates_to_ocr_contract(receipt_service, mock_ocr_service):
    analysis = await receipt_service.analyze(b"image")

    assert analysis.text == "MERCADO XYZ\nTotal: R$ 132,07"
    assert analysis.confidence == 88.5
    mock_ocr_service.extract_text.assert_awaited_once_with(b"image")


@pytest.mark.asyncio
async def test_build_message_uses_analysis_text(receipt_service):
    analysis = await receipt_service.analyze(b"image")

    message = receipt_service.build_message(analysis)

    assert "MERCADO XYZ" in message
    assert "132,07" in message


@pytest.mark.asyncio
async def test_analyze_propagates_ocr_error(mock_ocr_service):
    mock_ocr_service.extract_text.side_effect = RuntimeError("ocr down")
    service = ReceiptService(ocr_service=mock_ocr_service)

    with pytest.raises(RuntimeError, match="ocr down"):
        await service.analyze(b"image")
