from enum import Enum


class CardEnum(str, Enum):
    ITAU = "itau"
    PICPAY = "picpay"
    XP = "xp"
    NUBANK = "nubank"
    C6 = "c6"


class NameEnum(str, Enum):
    JOAO_LUCAS = "joao_lucas"
    LAILLA = "lailla"
