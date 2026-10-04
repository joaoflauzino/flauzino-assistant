import pytest
from unittest.mock import AsyncMock, MagicMock

from agent_api.core.exceptions import LLMProviderError
from agent_api.schemas.classify import (
    CategoryOption,
    ClassifyBatchRequest,
    ClassifyItemInput,
    LLMBatchClassificationResult,
    LLMItemClassification,
)
from agent_api.services.classify import ClassifyService


@pytest.fixture
def sample_request():
    return ClassifyBatchRequest(
        transactions=[
            ClassifyItemInput(
                id="1",
                merchant="PADARIA CENTRAL",
                raw_title="Débito de Cartão",
                raw_description="PADARIA CENTRAL Uberlandia",
                direction="OUT",
                amount=25.50,
            ),
            ClassifyItemInput(
                id="2",
                merchant="JOAO DA SILVA",
                raw_title="Pix enviado para JOAO DA SILVA",
                raw_description="TRANSF ENVIADA PIX",
                direction="OUT",
                amount=50.0,
            ),
            ClassifyItemInput(
                id="3",
                merchant="EMPRESA XYZ",
                raw_title="Salário",
                raw_description="Crédito em conta",
                direction="IN",
                amount=5000.0,
            ),
        ],
        expense_categories=[
            CategoryOption(key="alimentacao", display_name="Alimentação"),
            CategoryOption(key="transporte", display_name="Transporte"),
        ],
        income_categories=[
            CategoryOption(key="salario", display_name="Salário"),
        ],
    )


@pytest.mark.asyncio
async def test_classify_transactions_success(sample_request):
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=LLMBatchClassificationResult(
            items=[
                LLMItemClassification(id="1", category="alimentacao", confidence=0.9),
                LLMItemClassification(id="2", category=None, confidence=0.5),
                LLMItemClassification(id="3", category="salario", confidence=0.95),
            ]
        )
    )
    mock_llm.with_structured_output.return_value = mock_structured

    service = ClassifyService(llm=mock_llm)
    res = await service.classify_transactions(sample_request)

    assert len(res.suggestions) == 3
    assert res.suggestions[0].id == "1"
    assert res.suggestions[0].category == "alimentacao"
    assert res.suggestions[0].confidence == 0.9

    assert res.suggestions[1].id == "2"
    assert res.suggestions[1].category is None

    assert res.suggestions[2].id == "3"
    assert res.suggestions[2].category == "salario"


@pytest.mark.asyncio
async def test_classify_invalid_category_sanitized_to_none(sample_request):
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    # LLM inventa categoria 'categoria_inexistente' ou tenta colocar 'salario' para OUT
    mock_structured.ainvoke = AsyncMock(
        return_value=LLMBatchClassificationResult(
            items=[
                LLMItemClassification(id="1", category="categoria_inexistente", confidence=0.9),
                LLMItemClassification(
                    id="2", category="salario", confidence=0.9
                ),  # salario é só IN!
            ]
        )
    )
    mock_llm.with_structured_output.return_value = mock_structured

    service = ClassifyService(llm=mock_llm)
    res = await service.classify_transactions(sample_request)

    assert res.suggestions[0].category is None
    assert res.suggestions[1].category is None


@pytest.mark.asyncio
async def test_classify_empty_transactions():
    mock_llm = MagicMock()
    service = ClassifyService(llm=mock_llm)
    req = ClassifyBatchRequest(transactions=[])
    res = await service.classify_transactions(req)
    assert res.suggestions == []


@pytest.mark.asyncio
async def test_classify_llm_error_raises_llm_provider_error(sample_request):
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(side_effect=Exception("OpenAI API Timeout"))
    mock_llm.with_structured_output.return_value = mock_structured

    service = ClassifyService(llm=mock_llm)
    with pytest.raises(LLMProviderError):
        await service.classify_transactions(sample_request)
