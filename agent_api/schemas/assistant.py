from typing import Literal

from pydantic import BaseModel, Field

from agent_api.schemas.limit import LimitDetails
from agent_api.schemas.spending import SpendingDetails


class AssistantResponse(BaseModel):
    response_message: str = Field(
        ...,
        description="A resposta formatada para o usuário. Se faltar dados, peça-os educadamente.",
    )
    suggested_options: list[str] | None = Field(
        default=None,
        description="Lista de opções de botões curtos a serem apresentadas ao usuário (ex: ['Sim', 'Não']), se aplicável.",
    )
    is_complete: bool = Field(
        default=False,
        description="True se a operação solicitada foi concluída com sucesso ou a conversa foi encerrada. False se aguarda dados ou confirmação.",
    )
    image_base64: str | None = Field(
        default=None,
        description="Imagem em formato base64 caso um gráfico tenha sido gerado.",
    )

    # Campos mantidos com valores default para compatibilidade retroativa
    spending_details: SpendingDetails | None = Field(
        default=None,
        description="Detalhes do gasto se houver.",
    )
    limit_details: LimitDetails | None = Field(
        default=None,
        description="Detalhes do limite se houver.",
    )
    is_confirmed: bool = Field(
        default=False,
        description="True se confirmado pelo usuário.",
    )
    is_balance_query: bool = Field(
        default=False,
        description="True se consulta de saldo.",
    )
    requested_graph_type: Literal["bar", "pie"] | None = Field(
        default=None,
        description="Tipo de gráfico.",
    )
    requested_graph_categories: list[str] | None = Field(
        default=None,
        description="Categorias do gráfico.",
    )
    requested_graph_mode: str | None = Field(
        default=None,
        description="Modo do gráfico.",
    )
