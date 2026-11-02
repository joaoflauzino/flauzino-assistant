from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityNotFoundError
from finance_api.core.text import normalize_upper
from finance_api.models.category_rules import CategoryRule
from finance_api.repositories.category_rules import CategoryRuleRepositoryProtocol
from finance_api.schemas.classification import (
    ClassificationContext,
    ClassificationResult,
    PaymentType,
    RawTransactionText,
    TransactionKind,
)
from finance_api.services.ai_classifier import AIClassifierClient
from finance_api.services.classification_chain import build_default_classification_chain
from finance_api.services.classification_protocols import (
    ClassificationHandlerProtocol,
    MerchantExtractorPipeline,
)
from finance_api.services.extractors import get_default_extractor_pipeline
from finance_api.settings import settings

_PAYMENT_TYPE_PATTERNS: tuple[tuple[tuple[str, ...], PaymentType], ...] = (
    (("DEBITO DE CARTAO", "PAYGO*"), PaymentType.DEBIT),
    (("PIX",), PaymentType.PIX),
)


def resolve_default_payment_type(
    is_credit_card: bool,
    norm_combined: str,
) -> PaymentType:
    """Infers default PaymentType declaratively without branching cascade."""
    if is_credit_card:
        return PaymentType.CREDIT

    return next(
        (
            ptype
            for patterns, ptype in _PAYMENT_TYPE_PATTERNS
            if any(pat in norm_combined for pat in patterns)
        ),
        PaymentType.OTHER,
    )


class ClassificationService:
    def __init__(
        self,
        rule_repo: CategoryRuleRepositoryProtocol,
        ai_client: AIClassifierClient | None = None,
        chain_head: ClassificationHandlerProtocol | None = None,
        extractor_pipeline: MerchantExtractorPipeline | None = None,
    ) -> None:
        self.rule_repo = rule_repo
        self.ai_client = ai_client or AIClassifierClient()
        self._chain_head = chain_head or self._build_default_chain()
        self._extractor_pipeline = extractor_pipeline or get_default_extractor_pipeline()

    def _build_default_chain(self) -> ClassificationHandlerProtocol:
        return build_default_classification_chain(
            holder_names=self.get_own_holder_names(),
            rule_repo=self.rule_repo,
        )

    @handle_service_errors
    async def list_rules(self) -> Sequence[CategoryRule]:
        return await self.rule_repo.list_all()

    @handle_service_errors
    async def delete_rule(self, rule_id: UUID) -> None:
        deleted = await self.rule_repo.delete_by_id(rule_id)
        if not deleted:
            raise EntityNotFoundError(f"Regra com ID {rule_id} não encontrada.")

    def get_own_holder_names(self) -> list[str]:
        raw = settings.OWN_HOLDER_NAMES
        return [normalize_upper(n) for n in raw.split(",") if n.strip()]

    def is_own_transfer(self, text: str) -> bool:
        norm_text = normalize_upper(text)
        return any(name and name in norm_text for name in self.get_own_holder_names())

    def extract_merchant_location_desc(
        self, raw_title: str, raw_description: str | None, direction: str
    ) -> tuple[str, str | None, str]:
        title = (raw_title or "").strip()
        desc = (raw_description or "").strip()
        raw = RawTransactionText(
            title=title,
            description=desc,
            norm_title=normalize_upper(title),
            direction=direction,
        )
        extracted = self._extractor_pipeline(raw)
        return extracted.merchant, extracted.location, extracted.short_description

    async def classify_transaction(
        self,
        raw_title: str,
        raw_description: str | None,
        direction: str,
        amount: Decimal,
        bank_category: str | None = None,
        is_credit_card: bool = False,
    ) -> ClassificationResult:
        merchant, location, description = self.extract_merchant_location_desc(
            raw_title, raw_description, direction
        )
        norm_title = normalize_upper(raw_title)
        norm_desc = normalize_upper(raw_description or "")
        norm_combined = f"{norm_title} {norm_desc}".strip()

        default_payment_type = resolve_default_payment_type(
            is_credit_card=is_credit_card,
            norm_combined=norm_combined,
        )
        default_kind = TransactionKind.INCOME if direction == "IN" else TransactionKind.EXPENSE

        ctx = ClassificationContext(
            raw_title=raw_title,
            raw_description=raw_description,
            norm_title=norm_title,
            norm_desc=norm_desc,
            norm_combined=norm_combined,
            direction=direction,
            amount=amount,
            merchant=merchant,
            location=location,
            description=description,
            default_kind=default_kind,
            default_payment_type=default_payment_type,
            bank_category=bank_category,
            is_credit_card=is_credit_card,
        )
        return await self._chain_head.handle(ctx)
