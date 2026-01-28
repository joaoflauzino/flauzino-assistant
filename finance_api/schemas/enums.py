from enum import Enum


class CategoryEnum(str, Enum):
    FOOD = "alimentacao"
    EATING_OUT = "comer_fora"
    FARMACIES = "farmacia"
    MARKET = "mercado"
    TRANSPORT = "transporte"
    HOUSING = "moradia"
    HEALTH = "saude"
    LEISURE = "lazer"
    EDUCATION = "educação"
    SHOPPING = "compras"
    CLOTHING = "vestuario"
    TRAVEL = "viagem"
    SERVICES = "serviços"
    CHILDREN = "crianças"
    OTHER = "outros"


class CardEnum(str, Enum):
    ITAU = "itau"
    PICPAY = "picpay"
    XP = "xp"
    NUBANK = "nubank"
    C6 = "c6"


class NameEnum(str, Enum):
    JOAO_LUCAS = "joao_lucas"
    LAILLA = "lailla"
