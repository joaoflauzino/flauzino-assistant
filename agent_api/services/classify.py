import json
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agent_api.core.exceptions import LLMProviderError
from agent_api.core.logger import get_logger
from agent_api.schemas.classify import (
    ClassifyBatchRequest,
    ClassifyBatchResponse,
    ClassifySuggestion,
    LLMBatchClassificationResult,
)

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
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def classify_transactions(self, request: ClassifyBatchRequest) -> ClassifyBatchResponse:
        if not request.transactions:
            return ClassifyBatchResponse(suggestions=[])

        expense_keys = {cat.key: cat.display_name for cat in request.expense_categories}
        income_keys = {cat.key: cat.display_name for cat in request.income_categories}

        # Prepara payload simplificado para o prompt
        tx_payload = [
            {
                "id": t.id,
                "merchant": t.merchant,
                "raw_title": t.raw_title,
                "raw_description": t.raw_description,
                "direction": t.direction,
                "amount": t.amount,
            }
            for t in request.transactions
        ]

        user_content = (
            f"Categorias de Despesa permitidas (OUT):\n{json.dumps(expense_keys, ensure_ascii=False, indent=2)}\n\n"
            f"Categorias de Receita permitidas (IN):\n{json.dumps(income_keys, ensure_ascii=False, indent=2)}\n\n"
            f"Transações para classificar:\n{json.dumps(tx_payload, ensure_ascii=False, indent=2)}"
        )

        try:
            structured_llm = self.llm.with_structured_output(LLMBatchClassificationResult)
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_content),
            ]
            logger.info(f"Classifying {len(request.transactions)} transactions with LLM")
            result: LLMBatchClassificationResult = await structured_llm.ainvoke(messages)
        except Exception as e:
            logger.error(f"LLM classification failed: {e}", exc_info=True)
            raise LLMProviderError(f"Falha ao consultar provedor de LLM para classificação: {e}")

        # Validação Server-side rigorosa contra as categorias permitidas
        tx_dict = {t.id: t for t in request.transactions}
        result_map: dict[str, tuple[str | None, float | None]] = {}

        if result and getattr(result, "items", None):
            for item in result.items:
                target_tx = tx_dict.get(item.id)
                if not target_tx:
                    continue

                allowed = expense_keys if target_tx.direction == "OUT" else income_keys
                cat_candidate = item.category.strip().lower() if item.category else None
                if cat_candidate and cat_candidate in allowed:
                    result_map[item.id] = (
                        cat_candidate,
                        round(float(item.confidence), 2) if item.confidence is not None else 0.75,
                    )
                else:
                    result_map[item.id] = (None, None)

        # Monta resposta garantindo uma entrada para cada transação enviada
        suggestions: list[ClassifySuggestion] = []
        for t in request.transactions:
            cat, conf = result_map.get(t.id, (None, None))
            suggestions.append(ClassifySuggestion(id=t.id, category=cat, confidence=conf))

        return ClassifyBatchResponse(suggestions=suggestions)
