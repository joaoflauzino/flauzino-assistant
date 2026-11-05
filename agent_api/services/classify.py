import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agent_api.core.exceptions import LLMProviderError
from agent_api.core.logger import get_logger
from agent_api.schemas.classify import (
    ClassifyBatchRequest,
    ClassifyBatchResponse,
    ClassifyItemInput,
    ClassifySuggestion,
    LLMBatchClassificationResult,
    LLMItemClassification,
)
from agent_api.services.utils import build_tx_payload, normalize_confidence

logger = get_logger(__name__)

SYSTEM_PROMPT = """Você é um especialista em classificação financeira e categorização de extratos bancários brasileiros.
Sua missão é classificar cada transação na categoria mais adequada, usando ESTRITAMENTE as chaves fornecidas.

Regras fundamentais:
1. Para transações com direction="OUT" (saída/despesa): use SOMENTE as chaves de expense_categories.
2. Para transações com direction="IN" (entrada/receita): use SOMENTE as chaves de income_categories.
3. Se o comerciante ou descrição for um nome de pessoa física sem contexto comercial explícito (ex: 'ZILMA MARIA', 'FLAVIA PEREIRA'), ou se você não tiver certeza razoável, retorne category = null. Não tente adivinhar.
4. NUNCA invente uma categoria que não conste na lista correspondente. Se nenhuma se encaixar com confiança razoável, retorne category = null.
5. Atribua confidence entre 0.5 e 0.95 refletindo sua certeza.
6. Retorne um item para cada transação enviada, mantendo rigorosamente o mesmo id."""


class ClassifyService:
    def __init__(self, llm: BaseChatModel) -> None:
        self.llm = llm

    async def classify_transactions(self, request: ClassifyBatchRequest) -> ClassifyBatchResponse:
        if not request.transactions:
            return ClassifyBatchResponse(suggestions=[])

        expense_keys = {cat.key: cat.display_name for cat in request.expense_categories}
        income_keys = {cat.key: cat.display_name for cat in request.income_categories}

        result = await self._invoke_llm(request, expense_keys, income_keys)
        result_map = self._sanitize_suggestions(
            result,
            request.transactions,
            expense_keys,
            income_keys,
        )
        return self._assemble_response(request.transactions, result_map)

    async def _invoke_llm(
        self,
        request: ClassifyBatchRequest,
        expense_keys: dict[str, str],
        income_keys: dict[str, str],
    ) -> LLMBatchClassificationResult | None:
        user_content = self._build_user_content(
            expense_keys,
            income_keys,
            request.transactions,
        )
        try:
            structured_llm = self.llm.with_structured_output(LLMBatchClassificationResult)
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_content),
            ]
            logger.info(f"Classifying {len(request.transactions)} transactions with LLM")
            result = await structured_llm.ainvoke(messages)
            if isinstance(result, LLMBatchClassificationResult):
                return result
            if isinstance(result, dict):
                return LLMBatchClassificationResult.model_validate(result)
            return None
        except Exception as error:
            logger.error(f"LLM classification failed: {error}", exc_info=True)
            raise LLMProviderError(
                f"Falha ao consultar provedor de LLM para classificação: {error}"
            )

    def _build_user_content(
        self,
        expense_keys: dict[str, str],
        income_keys: dict[str, str],
        transactions: list[ClassifyItemInput],
    ) -> str:
        tx_payload = build_tx_payload(transactions)
        return (
            "Categorias de Despesa permitidas (OUT):\n"
            f"{json.dumps(expense_keys, ensure_ascii=False, indent=2)}\n\n"
            "Categorias de Receita permitidas (IN):\n"
            f"{json.dumps(income_keys, ensure_ascii=False, indent=2)}\n\n"
            f"Transações para classificar:\n{json.dumps(tx_payload, ensure_ascii=False, indent=2)}"
        )

    def _sanitize_suggestions(
        self,
        result: LLMBatchClassificationResult | None,
        transactions: list[ClassifyItemInput],
        expense_keys: dict[str, str],
        income_keys: dict[str, str],
    ) -> dict[str, tuple[str | None, float | None]]:
        if not result or not getattr(result, "items", None):
            return {}

        transaction_map = {transaction.id: transaction for transaction in transactions}
        result_map: dict[str, tuple[str | None, float | None]] = {}
        for item in result.items:
            target = transaction_map.get(item.id)
            if target is None:
                continue
            result_map[item.id] = self._sanitize_item(item, target, expense_keys, income_keys)
        return result_map

    def _sanitize_item(
        self,
        item: LLMItemClassification,
        target: ClassifyItemInput,
        expense_keys: dict[str, str],
        income_keys: dict[str, str],
    ) -> tuple[str | None, float | None]:
        allowed = expense_keys if target.direction == "OUT" else income_keys
        candidate = item.category.strip().lower() if item.category else None
        if candidate and candidate in allowed:
            return candidate, normalize_confidence(item.confidence)
        return None, None

    def _assemble_response(
        self,
        transactions: list[ClassifyItemInput],
        result_map: dict[str, tuple[str | None, float | None]],
    ) -> ClassifyBatchResponse:
        suggestions: list[ClassifySuggestion] = []
        for transaction in transactions:
            category, confidence = result_map.get(transaction.id, (None, None))
            suggestions.append(
                ClassifySuggestion(
                    id=transaction.id,
                    category=category,
                    confidence=confidence,
                )
            )
        return ClassifyBatchResponse(suggestions=suggestions)
