"""Schemas, default fallback values and DTOs for the finance client."""

_CACHE_TTL_SECONDS: float = 300.0  # 5 minutes

DEFAULT_CATEGORIES: list[str] = [
    "alimentacao",
    "comer_fora",
    "farmacia",
    "mercado",
    "transporte",
    "moradia",
    "saude",
    "lazer",
    "educação",
    "compras",
    "vestuario",
    "viagem",
    "serviços",
    "crianças",
    "outros",
]

DEFAULT_INCOME_CATEGORIES: list[str] = [
    "salario",
    "pix",
    "premiacao",
    "investimentos",
    "reembolso",
    "outros",
]

DEFAULT_PAYMENT_METHODS: list[str] = ["itau", "nubank", "picpay", "xp", "c6", "pix"]

DEFAULT_ACCOUNTS: list[str] = [
    "itau_joao",
    "nubank_joao",
    "nubank_lailla",
    "picpay_joao",
    "c6_joao",
]

DEFAULT_CREDIT_CARDS: list[str] = [
    "itau_card_joao",
    "nubank_card_joao",
    "nubank_card_lailla",
    "picpay_card_joao",
    "c6_card_joao",
]
