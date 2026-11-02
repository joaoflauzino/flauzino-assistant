"""Static fallbacks used when finance_api is unreachable while building keyboards."""

DEFAULT_CATEGORIES: list[str] = [
    "alimentacao",
    "comer_fora",
    "farmacia",
    "mercado",
    "transporte",
    "moradia",
    "saude",
    "lazer",
    "educacao",
    "compras",
    "vestuario",
    "viagem",
    "servicos",
    "criancas",
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

DEFAULT_PAYMENT_METHODS: list[str] = [
    "itau_card_joao",
    "nubank_card_joao",
    "nubank_card_lailla",
    "picpay_card_joao",
    "c6_card_joao",
    "itau_joao",
    "nubank_joao",
    "nubank_lailla",
    "picpay_joao",
    "c6_joao",
]

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

DEFAULT_OWNERS: list[str] = ["joao_lucas", "lailla"]
