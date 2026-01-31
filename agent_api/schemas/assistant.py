from pydantic import BaseModel, Field

from agent_api.schemas.limit import LimitDetails
from agent_api.schemas.spending import SpendingDetails


class AssistantResponse(BaseModel):
    response_message: str = Field(
        ...,
        description="A resposta para o usuário. Se faltar dados, peça-os aqui. Se estiver tudo certo, confirme o registro. Se não for sobre finanças, recuse educadamente.",
    )
    spending_details: SpendingDetails | None = Field(
        None,
        description="Os detalhes do gasto extraídos, se for um registro de gasto.",
    )
    limit_details: LimitDetails | None = Field(
        None,
        description="Os detalhes do limite extraídos, se for um cadastro de limite de gastos.",
    )
    is_complete: bool = Field(
        False,
        description="True apenas se TODAS as informações (categoria, valor, metodo_pagamento, local_compra) estiverem preenchidas.",
    )
    is_confirmed: bool = Field(
        False,
        description="True apenas se o usuário confirmar que os dados estão corretos.",
    )
