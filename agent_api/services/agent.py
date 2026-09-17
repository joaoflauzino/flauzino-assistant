from typing import Any, NotRequired, cast

from langchain.agents import AgentState, create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from agent_api.core.decorators import handle_llm_errors
from agent_api.core.logger import get_logger
from agent_api.schemas.assistant import AssistantResponse
from agent_api.services.finance import FinanceService
from agent_api.services.graph import GraphService
from agent_api.services.tools import create_agent_tools

logger = get_logger(__name__)


class AgentStateWithImage(AgentState):
    image_base64: NotRequired[str | None]


class AgentService:
    """Encapsulates LangChain agent lifecycle, tool execution, and prompt generation."""

    def __init__(
        self,
        llm: BaseChatModel,
        finance_service: FinanceService,
        graph_service: GraphService,
    ):
        self.llm = llm
        self.finance_service = finance_service
        self.graph_service = graph_service
        self.tools = create_agent_tools(finance_service, graph_service)

    async def get_system_prompt(self, platform: str | None = None) -> str:
        """Dynamically generate system prompt with valid categories and payment methods."""
        try:
            categories = await self.finance_service.get_categories()
            valid_categories = ", ".join([f"'{c}'" for c in categories])
            payment_methods = await self.finance_service.get_payment_methods()
            valid_payment_methods = ", ".join([f"'{m}'" for m in payment_methods])
        except Exception as e:
            logger.warning(
                f"Failed to fetch dynamic financial metadata for system prompt: {e}. Falling back to empty lists."
            )
            valid_categories = ""
            valid_payment_methods = ""

        platform_instructions = ""
        if platform == "telegram":
            platform_instructions = (
                "**Formatação para Telegram**:\n"
                "- A formatação deve ser visualmente agradável com espaçamento generoso.\n"
                "- Use quebras de linha duplas entre seções.\n"
                "- Emojis com moderação para legibilidade.\n"
                "- Destaque valores e categorias em negrito.\n"
                "- Mantenha a resposta concisa e direta, sem introduções desnecessárias."
            )
        elif platform == "web":
            platform_instructions = (
                "**Formatação para Web**:\n"
                "- A formatação deve ser limpa, direta e formal-objetiva.\n"
                "- Evite saudações excessivas."
            )

        return f"""
        Você é o assistente financeiro inteligente da Família Flauzino.
        Seu objetivo é gerenciar as finanças familiares através das ferramentas disponíveis:
        - Consultar saldos e limites de gastos
        - Registrar novos gastos (despesas)
        - Cadastrar limites de gastos por categoria
        - Gerar gráficos visuais comparativos e de distribuição

        **CATEGORIAS VÁLIDAS**:
        O campo `categoria` DEVE ser estritamente uma destas opções:
        [{valid_categories}]

        **MÉTODOS DE PAGAMENTO VÁLIDOS**:
        O campo `metodo_pagamento` DEVE ser estritamente uma destas opções:
        [{valid_payment_methods}]

        ### DIRETRIZES DE USO DAS FERRAMENTAS E FLUXO:

        1. **Consulta de Saldos e Limites**:
        - Se o usuário perguntar sobre saldos, limites ou quanto ainda pode gastar, chame a ferramenta `consultar_saldos(categorias=...)`.
        - Se ele especificou categorias, passe a lista de categorias. Se não especificou ou pediu no geral, passe `None` para consultar todas.
        - Analise o retorno da ferramenta e formule uma resposta clara, educada e resumida ao usuário.

        2. **Geração de Gráficos**:
        - Se o usuário pedir explicitamente um gráfico, chart ou visualização (ex: "gere um gráfico dos limites", "pizza dos gastos", "gráfico de barras com meus saldos"):
          - Chame a ferramenta `gerar_grafico(tipo=..., categorias=..., modo=...)`.
          - Use `tipo="pie"` para gráfico de pizza (proporção de gastos).
          - Use `tipo="bar"` para gráfico de barras (comparativo de limites e saldos).
          - No modo de barras: use "saldo" (limite vs gasto) ou "gastos" (apenas gastos). Padrão é "saldo".
          - Após a ferramenta gerar o gráfico, informe ao usuário que o gráfico foi gerado e apresentado.

        3. **Registro de Gastos (REGRA CRÍTICA DE CONFIRMAÇÃO)**:
        - Para registrar um gasto, você precisa de: `categoria`, `valor`, `item_comprado`, `metodo_pagamento`, `local_compra`.
        - Se faltar qualquer informação: pergunte educadamente pelos dados faltantes. Liste o que falta usando hífens (-) (nunca use tags HTML).
        - JAMAIS infira a categoria ou método de pagamento se houver ambiguidade. Confirme com o usuário.
        - **REGRA CRÍTICA**: NUNCA chame a ferramenta `registrar_gasto` no primeiro momento em que o usuário fornecer os dados. Primeiro, apresente os dados em formato de lista com hífens e pergunte se ele confirma o registro (fornecendo opções sugeridas como `["Sim", "Não"]`).
        - Somente após o usuário responder afirmativamente (ex: "Sim", "Confirmo", "Pode registrar") no histórico da conversa, chame a ferramenta `registrar_gasto`.

        4. **Cadastro de Limites de Gastos (REGRA CRÍTICA DE CONFIRMAÇÃO)**:
        - Para cadastrar um limite, você precisa de: `categoria` e `valor`.
        - Confirme os dados com o usuário antes de chamar `cadastrar_limite`.
        - Chame `cadastrar_limite` apenas após confirmação afirmativa do usuário.

        5. **Formato da Resposta Final**:
        - `response_message`: O texto final que será enviado ao usuário (formatado para a plataforma).
        - `suggested_options`: Forneça até 3 opções curtas de botões caso esteja fazendo uma pergunta de confirmação ou escolha simples (ex: `["Sim", "Não"]`). Se não houver, deixe nulo ou vazio.
        - `is_complete`:
          - Defina como `True` se o objetivo do usuário foi concluído com sucesso (ex: gasto registrado, limite cadastrado, ou gráfico/saldo entregue e o usuário agradeceu como "obrigado", "valeu", "era só isso").
          - Defina como `False` se a interação ainda estiver em andamento (aguardando dados faltantes, aguardando confirmação "Sim/Não", etc.).

        {platform_instructions}
    """

    @handle_llm_errors
    async def get_response(
        self,
        chat_history: list[dict[str, Any]],
        platform: str | None = None,
    ) -> AssistantResponse:
        """Run agent with LangChain create_agent."""
        system_prompt = await self.get_system_prompt(platform=platform)

        agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt,
            response_format=AssistantResponse,
            state_schema=AgentStateWithImage,
        )

        messages: list[BaseMessage] = []
        for msg in chat_history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))

        agent_input = cast(Any, {"messages": messages})
        result = await agent.ainvoke(agent_input)

        structured_resp: AssistantResponse | None = result.get("structured_response")
        image_base64 = result.get("image_base64")

        if structured_resp is not None:
            if image_base64:
                structured_resp.image_base64 = image_base64
            return structured_resp

        # Fallback caso o modelo retorne texto simples
        msgs = result.get("messages", [])
        last_msg = msgs[-1] if msgs else None
        response_text = (
            str(last_msg.content)
            if last_msg and last_msg.content
            else "Desculpe, não consegui processar sua mensagem."
        )
        return AssistantResponse(
            response_message=response_text,
            image_base64=image_base64,
            is_complete=False,
        )
