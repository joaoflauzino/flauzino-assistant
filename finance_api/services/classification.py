from dataclasses import dataclass
from decimal import Decimal
import re
import unicodedata

from finance_api.repositories.category_rules import CategoryRuleRepository
from finance_api.services.ai_classifier import AIClassifierClient
from finance_api.settings import settings


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


@dataclass
class ClassificationResult:
    merchant: str
    kind: str  # EXPENSE, INCOME, TRANSFER, INVOICE_PAYMENT, REFUND
    payment_type: str
    suggested_category: str | None
    suggestion_source: str | None  # RULE, MEMORY, LLM
    confidence: Decimal | None
    description: str
    location: str | None = None


# Mapeamento heurístico de categorias fornecidas por bancos (ex: C6) para categorias do sistema
BANK_CATEGORY_MAP: dict[str, tuple[str, Decimal]] = {
    "RESTAURANTE / LANCHONETE / BAR": ("comer_fora", Decimal("0.950")),
    "SUPERMERCADOS / MERCEARIA / PADARIAS / LOJAS DE CONVENIENCIA": ("mercado", Decimal("0.950")),
    "ASSISTENCIA MEDICA E ODONTOLOGICA": ("saude", Decimal("0.950")),
    "TRANSPORTE": ("transporte", Decimal("0.950")),
    "RELACIONADOS A AUTOMOTIVO": ("transporte", Decimal("0.900")),
    "TV POR ASSINATURA / SERVICOS DE RADIO": ("servicos", Decimal("0.950")),
    "SERVICOS DE TELECOMUNICACOES": ("servicos", Decimal("0.950")),
    "VESTUARIO / ROUPAS": ("vestuario", Decimal("0.950")),
    "ALUGUEL": ("moradia", Decimal("0.900")),
    "ESPECIALIDADE VAREJO": ("compras", Decimal("0.850")),
    "DEPARTAMENTO / DESCONTO": ("compras", Decimal("0.850")),
    "T&E": ("viagem", Decimal("0.900")),
    "MARKETING DIRETO": ("outros", Decimal("0.800")),
    "SERVICOS PESSOAIS": ("servicos", Decimal("0.850")),
}


class ClassificationService:
    def __init__(
        self,
        rule_repo: CategoryRuleRepository,
        ai_client: AIClassifierClient | None = None,
    ):
        self.rule_repo = rule_repo
        self.ai_client = ai_client or AIClassifierClient()

    def get_own_holder_names(self) -> list[str]:
        raw = settings.OWN_HOLDER_NAMES
        return [_normalize(n) for n in raw.split(",") if n.strip()]

    def is_own_transfer(self, text: str) -> bool:
        norm_text = _normalize(text)
        for name in self.get_own_holder_names():
            if name and name in norm_text:
                return True
        return False

    def extract_merchant_location_desc(
        self, raw_title: str, raw_description: str | None, direction: str
    ) -> tuple[str, str | None, str]:
        title = (raw_title or "").strip()
        desc = (raw_description or "").strip()
        norm_title = _normalize(title)

        # 0. Pagamento de fatura e taxas de cartão
        if "INCLUSAO DE PAGAMENTO" in norm_title or "PGTO FAT CARTAO" in norm_title:
            return "C6 BANK", None, "Pagamento de Fatura"
        if "ANUIDADE" in norm_title:
            return "C6 BANK", None, "Anuidade Cartão"
        if "ESTORNO TARIFA" in norm_title or "ESTORNO" in norm_title:
            return "C6 BANK", None, "Estorno Tarifa"

        # 1. Cartão de Débito / Crédito format (ex: PAYGO*AUGUSTS BURGE    Uberlandia    BRA. Cartão 1633)
        if desc and ("PAYGO*" in desc or "CARTAO" in _normalize(title)):
            m = re.search(
                r"PAYGO\*([^\s]+(?:\s+[^\s]+)*?)\s{2,}([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)*?)\s+BRA",
                desc,
            )
            if m:
                merchant = m.group(1).strip()
                location = m.group(2).strip()
                return merchant, location, (title if len(title) <= 50 else merchant[:50])
            m2 = re.search(r"PAYGO\*([^.]+?)(?:\s{2,}|\.|$)", desc)
            if m2:
                merchant = m2.group(1).strip()
                return merchant, "Uberlândia", (title if len(title) <= 50 else merchant[:50])

        # 2. Pix enviado para X
        m_pix_env = re.search(r"Pix enviado para\s+(.+)", title, re.IGNORECASE)
        if m_pix_env:
            merchant = m_pix_env.group(1).strip()
            return merchant, None, (f"Pix {merchant}"[:50])

        # 3. Pix recebido de X
        m_pix_rec = re.search(r"Pix recebido de\s+(.+)", title, re.IGNORECASE)
        if m_pix_rec:
            merchant = m_pix_rec.group(1).strip()
            return merchant, None, (f"Pix de {merchant}"[:50])

        # 4. Devol recebida pix de X
        m_devol = re.search(r"Devol recebida pix(?: de)?\s*(.+)?", title, re.IGNORECASE)
        if m_devol and m_devol.group(1):
            merchant = m_devol.group(1).strip()
            return merchant, None, (title[:50])

        # 5. Salário / PPR
        if any(k in norm_title for k in ["CRED SALARIO", "ADTO SALARIO", "PAGAMENTO PPR", "PLR"]):
            return "C6 BANK", None, (title[:50])

        # Fallback padrão
        merchant = title if title else (desc if desc else "Transação")
        location = None
        short_desc = title[:50] if title else "Transação"
        return merchant, location, short_desc

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
        norm_title = _normalize(raw_title)
        norm_desc = _normalize(raw_description or "")
        norm_combined = f"{norm_title} {norm_desc}"

        # ---------------------------------------------------------
        # Camada 1: Regras Determinísticas de Tipo
        # ---------------------------------------------------------
        # 1.1 Transferência entre contas próprias
        if self.is_own_transfer(norm_combined):
            return ClassificationResult(
                merchant=merchant,
                kind="TRANSFER",
                payment_type="PIX" if "PIX" in norm_combined else "TRANSFER",
                suggested_category=None,
                suggestion_source="RULE",
                confidence=Decimal("1.000"),
                description=description,
                location=location,
            )

        # 1.2 Pagamento de fatura de cartão
        if any(
            inv_pat in norm_combined
            for inv_pat in [
                "INCLUSAO DE PAGAMENTO",
                "PGTO FAT CARTAO",
                "FATURA DE CARTAO",
                "NU PAGAMENTOS",
                "BRADESCARD",
            ]
        ):
            return ClassificationResult(
                merchant="C6 BANK",
                kind="INVOICE_PAYMENT",
                payment_type="CREDIT" if is_credit_card else "DEBIT",
                suggested_category=None,
                suggestion_source="RULE",
                confidence=Decimal("1.000"),
                description=description,
                location=location,
            )

        # 1.3 Estorno / Reembolso
        if "DEVOL RECEBIDA PIX" in norm_title or "ESTORNO" in norm_combined:
            return ClassificationResult(
                merchant=merchant,
                kind="REFUND",
                payment_type="CREDIT" if is_credit_card else "PIX",
                suggested_category=None,
                suggestion_source="RULE",
                confidence=Decimal("0.950"),
                description=description,
                location=location,
            )

        # 1.4 Anuidade do Cartão
        if "ANUIDADE" in norm_title:
            return ClassificationResult(
                merchant="C6 BANK",
                kind="EXPENSE",
                payment_type="CREDIT",
                suggested_category="servicos",
                suggestion_source="RULE",
                confidence=Decimal("0.950"),
                description=description,
                location=location,
            )

        # 1.5 Receitas de Salário e PLR
        if "CRED SALARIO" in norm_title or "ADTO SALARIO" in norm_title:
            return ClassificationResult(
                merchant="C6 BANK",
                kind="INCOME",
                payment_type="OTHER",
                suggested_category="salario",
                suggestion_source="RULE",
                confidence=Decimal("0.980"),
                description=description,
                location=location,
            )
        if "PPR" in norm_title or "PLR" in norm_title:
            return ClassificationResult(
                merchant="C6 BANK",
                kind="INCOME",
                payment_type="OTHER",
                suggested_category="premiacao",
                suggestion_source="RULE",
                confidence=Decimal("0.980"),
                description=description,
                location=location,
            )

        # 1.6 Pix recebido de terceiros (INCOME padrão)
        if direction == "IN" and ("PIX RECEBIDO" in norm_title or "TRANSF RECEBIDA" in norm_title):
            return ClassificationResult(
                merchant=merchant,
                kind="INCOME",
                payment_type="PIX",
                suggested_category="pix",
                suggestion_source="RULE",
                confidence=Decimal("0.800"),
                description=description,
                location=location,
            )

        # Tipo padrão de pagamento
        default_payment_type = "CREDIT" if is_credit_card else "OTHER"
        if not is_credit_card:
            if "DEBITO DE CARTAO" in norm_title or "PAYGO*" in norm_desc:
                default_payment_type = "DEBIT"
            elif "PIX" in norm_combined:
                default_payment_type = "PIX"

        default_kind = "INCOME" if direction == "IN" else "EXPENSE"

        # ---------------------------------------------------------
        # Camada 2: Memória de Comerciantes (category_rules)
        # ---------------------------------------------------------
        matched_rule = await self.rule_repo.find_matching_rule(merchant, direction)
        if matched_rule and matched_rule.category:
            await self.rule_repo.increment_hits(matched_rule.id)
            source = "RULE" if matched_rule.source == "SEED" else "MEMORY"
            conf = Decimal("0.950") if matched_rule.hits >= 2 else Decimal("0.850")
            return ClassificationResult(
                merchant=merchant,
                kind=matched_rule.kind,
                payment_type=default_payment_type,
                suggested_category=matched_rule.category,
                suggestion_source=source,
                confidence=conf,
                description=description,
                location=location,
            )

        # ---------------------------------------------------------
        # Camada 2.5: Categoria Fornecida pelo Banco (ex: C6)
        # ---------------------------------------------------------
        if bank_category and default_kind == "EXPENSE":
            norm_bcat = _normalize(bank_category)
            if norm_bcat in BANK_CATEGORY_MAP:
                sug_cat, conf = BANK_CATEGORY_MAP[norm_bcat]
                return ClassificationResult(
                    merchant=merchant,
                    kind=default_kind,
                    payment_type=default_payment_type,
                    suggested_category=sug_cat,
                    suggestion_source="RULE",
                    confidence=conf,
                    description=description,
                    location=location,
                )

        # Sem categoria ainda — aguarda LLM na fase em lote
        return ClassificationResult(
            merchant=merchant,
            kind=default_kind,
            payment_type=default_payment_type,
            suggested_category=None,
            suggestion_source=None,
            confidence=None,
            description=description,
            location=location,
        )
