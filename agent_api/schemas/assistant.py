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
    is_balance_query: bool = Field(
        False,
        description="True se o usuário estiver perguntando sobre o saldo, limite ou o quanto ainda pode gastar de categorias. NUNCA peça para o usuário especificar a categoria. Se ele não especificar, assuma que é para todas e defina como True imediatamente.",
    )
    suggested_options: list[str] | None = Field(
        None,
        description="Lista de opções de botões a serem apresentadas ao usuário, caso o assistente queira que ele escolha. NUNCA use isso para pedir para o usuário escolher categorias de saldo ou limite; se ele não especificar, assuma que ele quer ver todas automaticamente.",
    )
    requested_graph_type: str | None = Field(
        None,
        description="Pode ser 'plot_category_balance' ou 'plot_expense_pie_chart'. Preencha com 'plot_category_balance' SEMPRE que o usuário perguntar sobre saldo, limites, gastos ou o quanto ainda pode gastar (mesmo que não peça um gráfico explicitamente). Use 'plot_expense_pie_chart' para distribuição de gastos.",
    )
    requested_graph_categories: list[str] | None = Field(
        None,
        description="Lista de categorias a serem passadas para o gráfico, se o usuário tiver pedido um gráfico de categorias específicas. Deixe nulo para todas.",
    )
    requested_graph_mode: str | None = Field(
        None,
        description="Pode ser 'saldo' ou 'limites'. Opcional.",
    )
