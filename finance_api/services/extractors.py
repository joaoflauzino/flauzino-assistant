"""Pure stateless functions and builder for merchant and location extraction."""

import re

from finance_api.schemas.classification import ExtractedMerchantInfo, RawTransactionText
from finance_api.services.protocols import MerchantExtractorPipeline, MerchantExtractorStep


def extract_card_fees_and_invoice(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    if "INCLUSAO DE PAGAMENTO" in raw.norm_title or "PGTO FAT CARTAO" in raw.norm_title:
        return ExtractedMerchantInfo("C6 BANK", None, "Pagamento de Fatura")
    if "ANUIDADE" in raw.norm_title:
        return ExtractedMerchantInfo("C6 BANK", None, "Anuidade Cartão")
    if "ESTORNO TARIFA" in raw.norm_title or "ESTORNO" in raw.norm_title:
        return ExtractedMerchantInfo("C6 BANK", None, "Estorno Tarifa")
    return None


def extract_paygo_card(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    if not raw.description or ("PAYGO*" not in raw.description and "CARTAO" not in raw.norm_title):
        return None

    match_city = re.search(
        r"PAYGO\*([^\s]+(?:\s+[^\s]+)*?)\s{2,}([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)*?)\s+BRA",
        raw.description,
    )
    if match_city:
        merchant = match_city.group(1).strip()
        location = match_city.group(2).strip()
        short_desc = raw.title if len(raw.title) <= 50 else merchant[:50]
        return ExtractedMerchantInfo(merchant, location, short_desc)

    match_fallback = re.search(r"PAYGO\*([^.]+?)(?:\s{2,}|\.|$)", raw.description)
    if match_fallback:
        merchant = match_fallback.group(1).strip()
        short_desc = raw.title if len(raw.title) <= 50 else merchant[:50]
        return ExtractedMerchantInfo(merchant, "Uberlândia", short_desc)

    return None


def extract_pix_sent(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    match = re.search(r"Pix enviado para\s+(.+)", raw.title, re.IGNORECASE)
    if not match:
        return None
    merchant = match.group(1).strip()
    return ExtractedMerchantInfo(merchant, None, f"Pix {merchant}"[:50])


def extract_pix_received(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    match = re.search(r"Pix recebido de\s+(.+)", raw.title, re.IGNORECASE)
    if not match:
        return None
    merchant = match.group(1).strip()
    return ExtractedMerchantInfo(merchant, None, f"Pix de {merchant}"[:50])


def extract_pix_refund(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    match = re.search(r"Devol recebida pix(?: de)?\s*(.+)?", raw.title, re.IGNORECASE)
    if not match or not match.group(1):
        return None
    merchant = match.group(1).strip()
    return ExtractedMerchantInfo(merchant, None, raw.title[:50])


def extract_salary_or_bonus(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    keywords = ("CRED SALARIO", "ADTO SALARIO", "PAGAMENTO PPR", "PLR")
    if any(k in raw.norm_title for k in keywords):
        return ExtractedMerchantInfo("C6 BANK", None, raw.title[:50])
    return None


DEFAULT_EXTRACTOR_STEPS: tuple[MerchantExtractorStep, ...] = (
    extract_card_fees_and_invoice,
    extract_paygo_card,
    extract_pix_sent,
    extract_pix_received,
    extract_pix_refund,
    extract_salary_or_bonus,
)


def build_extractor_pipeline(
    *steps: MerchantExtractorStep,
) -> MerchantExtractorPipeline:
    """Compõe os passos de extração em uma cadeia com short-circuit e fallback padrão."""

    def run(raw: RawTransactionText) -> ExtractedMerchantInfo:
        for step in steps:
            result = step(raw)
            if result is not None:
                return result
        merchant = raw.title or raw.description or "Transação"
        short_desc = raw.title[:50] if raw.title else "Transação"
        return ExtractedMerchantInfo(merchant, None, short_desc)

    return run


def get_default_extractor_pipeline() -> MerchantExtractorPipeline:
    return build_extractor_pipeline(*DEFAULT_EXTRACTOR_STEPS)
