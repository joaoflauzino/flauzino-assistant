from finance_api.core.text import normalize_upper
from finance_api.schemas.classification import (
    ExtractedMerchantInfo,
    RawTransactionText,
)
from finance_api.services.extractors import (
    build_extractor_pipeline,
    extract_card_fees_and_invoice,
    extract_paygo_card,
    extract_pix_received,
    extract_pix_refund,
    extract_pix_sent,
    extract_salary_or_bonus,
    get_default_extractor_pipeline,
)


def _make_raw(
    title: str = "",
    description: str = "",
    direction: str = "OUT",
) -> RawTransactionText:
    norm_title = normalize_upper(title)
    return RawTransactionText(
        title=title,
        description=description,
        norm_title=norm_title,
        direction=direction,
    )


def test_extract_card_fees_and_invoice() -> None:
    # Inclusao de pagamento / Pgto fatura
    raw1 = _make_raw("INCLUSAO DE PAGAMENTO AUTOMATICO")
    info1 = extract_card_fees_and_invoice(raw1)
    assert info1 == ExtractedMerchantInfo("C6 BANK", None, "Pagamento de Fatura")

    raw2 = _make_raw("PGTO FAT CARTAO C6")
    info2 = extract_card_fees_and_invoice(raw2)
    assert info2 == ExtractedMerchantInfo("C6 BANK", None, "Pagamento de Fatura")

    # Anuidade
    raw3 = _make_raw("ANUIDADE DIFERENCIADA")
    info3 = extract_card_fees_and_invoice(raw3)
    assert info3 == ExtractedMerchantInfo("C6 BANK", None, "Anuidade Cartão")

    # Estorno
    raw4 = _make_raw("ESTORNO TARIFA CONTA")
    info4 = extract_card_fees_and_invoice(raw4)
    assert info4 == ExtractedMerchantInfo("C6 BANK", None, "Estorno Tarifa")

    # Non-matching
    raw5 = _make_raw("COMPRA PADARIA")
    assert extract_card_fees_and_invoice(raw5) is None


def test_extract_paygo_card_with_city() -> None:
    raw = _make_raw(
        title="Compra no Débito",
        description="PAYGO*AUGUSTS BURGE    Uberlandia    BRA. Cartão 1633",
    )
    info = extract_paygo_card(raw)
    assert info is not None
    assert info.merchant == "AUGUSTS BURGE"
    assert info.location == "Uberlandia"
    assert info.short_description == "Compra no Débito"


def test_extract_paygo_card_fallback_city() -> None:
    raw = _make_raw(
        title="Compra Cartao Supermercado com titulo muito longo que ultrapassa cinquenta caracteres",
        description="PAYGO*SUPERMERCADO ABC.",
    )
    info = extract_paygo_card(raw)
    assert info is not None
    assert info.merchant == "SUPERMERCADO ABC"
    assert info.location == "Uberlândia"
    assert info.short_description == "SUPERMERCADO ABC"[:50]


def test_extract_paygo_card_non_matching() -> None:
    raw = _make_raw(title="Pix enviado", description="Sem paygo aqui")
    assert extract_paygo_card(raw) is None

    # Has CARTAO in norm_title and non-empty description, but no PAYGO* regex match
    raw_cartao_no_paygo = _make_raw(
        title="COMPRA CARTAO DEBITO",
        description="ESTABELECIMENTO SEM PREFIXO PAYGO",
    )
    assert extract_paygo_card(raw_cartao_no_paygo) is None


def test_extract_pix_sent() -> None:
    raw = _make_raw(title="Pix enviado para Drogaria Sao Paulo")
    info = extract_pix_sent(raw)
    assert info is not None
    assert info.merchant == "Drogaria Sao Paulo"
    assert info.location is None
    assert info.short_description == "Pix Drogaria Sao Paulo"

    raw_none = _make_raw(title="TED enviada para Fulano")
    assert extract_pix_sent(raw_none) is None


def test_extract_pix_received() -> None:
    raw = _make_raw(title="Pix recebido de Maria Souza")
    info = extract_pix_received(raw)
    assert info is not None
    assert info.merchant == "Maria Souza"
    assert info.location is None
    assert info.short_description == "Pix de Maria Souza"

    raw_none = _make_raw(title="Boleto pago")
    assert extract_pix_received(raw_none) is None


def test_extract_pix_refund() -> None:
    raw = _make_raw(title="Devol recebida pix de Loja Exemplo")
    info = extract_pix_refund(raw)
    assert info is not None
    assert info.merchant == "Loja Exemplo"
    assert info.location is None
    assert info.short_description == "Devol recebida pix de Loja Exemplo"

    raw_none = _make_raw(title="Transferência Comum")
    assert extract_pix_refund(raw_none) is None


def test_extract_salary_or_bonus() -> None:
    for kw in ("CRED SALARIO", "ADTO SALARIO", "PAGAMENTO PPR", "PLR"):
        raw = _make_raw(title=f"TESTE {kw} LIQUIDO")
        info = extract_salary_or_bonus(raw)
        assert info is not None
        assert info.merchant == "C6 BANK"
        assert info.location is None

    raw_none = _make_raw(title="Lançamento qualquer")
    assert extract_salary_or_bonus(raw_none) is None


def test_build_extractor_pipeline_fallback() -> None:
    pipeline = build_extractor_pipeline()  # empty steps -> always falls back
    raw = _make_raw(title="Mercadinho Local", description="Compra avulsa")
    info = pipeline(raw)
    assert info.merchant == "Mercadinho Local"
    assert info.location is None
    assert info.short_description == "Mercadinho Local"

    # Empty title uses description
    raw_no_title = _make_raw(title="", description="Descricao apenas")
    info_no_title = pipeline(raw_no_title)
    assert info_no_title.merchant == "Descricao apenas"
    assert info_no_title.short_description == "Transação"

    # Both empty defaults to "Transação"
    raw_empty = _make_raw(title="", description="")
    info_empty = pipeline(raw_empty)
    assert info_empty.merchant == "Transação"
    assert info_empty.short_description == "Transação"


def test_get_default_extractor_pipeline() -> None:
    pipeline = get_default_extractor_pipeline()
    raw = _make_raw(title="Pix enviado para Farmacia Popular")
    info = pipeline(raw)
    assert info.merchant == "Farmacia Popular"
    assert info.short_description == "Pix Farmacia Popular"
