from typing import Any, NotRequired, cast

from langchain.agents import AgentState, create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from agent_api.core.callbacks import AgentLoggingCallbackHandler
from agent_api.core.decorators import handle_llm_errors
from agent_api.core.logger import get_logger
from agent_api.schemas.assistant import AssistantResponse
from agent_api.services.finance import FinanceService
from agent_api.services.graph import GraphService
from agent_api.services.tools import create_agent_tools

logger = get_logger(__name__)


class AgentStateWithCustom(AgentState):
    image_base64: NotRequired[str | None]
    final_response: NotRequired[dict[str, Any] | None]


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

        ### REGRAS DE NEGÓCIO:

        0. **Saudações e Conversas Informais**:
        - Se o usuário apenas cumprimentar ("olá", "oi", etc.):
          - Responda cordialmente apresentando o que você pode fazer.
          - Sugira opções nos botões (ex: ["Registrar gasto", "Consultar saldos", "Cadastrar limite"]).
          - Defina `is_complete=False`.
          - NUNCA chame ferramentas financeiras para simples cumprimentos.

        1. **Registro de Gastos (REGRA CRÍTICA DE CONFIRMAÇÃO)**:
        - Para registrar um gasto, você precisa de: `categoria`, `valor`, `item_comprado`, `metodo_pagamento`, `local_compra`.
        - Se faltar qualquer informação:
          - Pergunte ao usuário os dados faltantes com `suggested_options=[]` e `is_complete=False`.
        - Quando o usuário fornecer todos os dados:
          - Apresente os dados em formato de lista com hífens (-).
          - Pergunte a confirmação ao usuário com `suggested_options=["Sim", "Não"]` e `is_complete=False`.
          - NUNCA chame `registrar_gasto` antes de receber o "Sim" / confirmação do usuário.
        - Somente após o usuário confirmar expressamente:
          - Chame `registrar_gasto(...)`.
          - E em seguida responda confirmando o sucesso do registro com `is_complete=True`.

        2. **Cadastro de Limites de Gastos**:
        - Confirme os dados antes de registrar (`suggested_options=["Sim", "Não"]`, `is_complete=False`).
        - Chame `cadastrar_limite` após confirmação e depois responda com `is_complete=True`.

        3. **Consulta de Saldos e Limites**:
        - Chame `consultar_saldos(categorias=...)`.
        - Formule a resposta com o resumo, `is_complete=False` (para permitir que o usuário faça perguntas adicionais) e opções sugeridas como ["Registrar gasto", "Gerar gráfico", "Tudo certo"].

        4. **Geração de Gráficos e Ajustes Visuais**:
        - Chame `gerar_grafico(...)`.
        - Em seguida, avise que o gráfico foi gerado com `is_complete=False` (para permitir que o usuário peça ajustes como "faz em barras", "mostra só mercado", etc.) e opções como ["Gráfico de pizza", "Gráfico de barras", "Tudo certo"].

        5. **Encerramento de Conversas**:
        - Se o usuário agradecer ou disser que terminou (ex: "obrigado", "valeu", "ok", "tudo certo", "só isso", "era isso"):
          - Responda agradecendo educadamente com `suggested_options=[]` e `is_complete=True`.
        - Se o usuário pedir follow-up ou correção (ex: "corrige pra barras", "e alimentação?"):
          - Mantenha `is_complete=False`.

        6. **Leitura de Recibos, Comprovantes e Notas Fiscais (OCR)**:
        - Ao receber texto extraído de recibo ou comprovante:
          - NUNCA responda apenas dizendo que vai analisar, organizar ou verificar os dados.
          - Analise e apresente IMEDIATAMENTE na mesma resposta todos os dados identificados (ex: valor total, local/estabelecimento, data, itens).
          - Aponte com clareza quais campos obrigatórios ainda faltam (`categoria`, `item_comprado`, `metodo_pagamento`, `local_compra`) para registrar o gasto.
          - Se faltar método de pagamento ou categoria, liste as opções válidas para o usuário escolher.
          - Defina `is_complete=False`.

        {platform_instructions}
    """

    @handle_llm_errors
    async def get_response(
        self,
        chat_history: list[dict[str, Any]],
        platform: str | None = None,
    ) -> AssistantResponse:
        """Run agent with LangChain create_agent and extract response via ToolStrategy(AssistantResponse)."""
        system_prompt = await self.get_system_prompt(platform=platform)

        agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt,
            response_format=ToolStrategy(schema=AssistantResponse),
            state_schema=AgentStateWithCustom,
        )

        messages: list[BaseMessage] = []
        for msg in chat_history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))

        callback_handler = AgentLoggingCallbackHandler()
        agent_input = cast(Any, {"messages": messages})
        result = await agent.ainvoke(
            agent_input,
            config={"callbacks": [callback_handler]},
        )

        # Logging detalhado do que o agent.ainvoke produziu
        msgs = result.get("messages", [])
        msgs_summary = [
            f"{type(m).__name__}(content={repr(m.content)[:80]}, tool_calls={getattr(m, 'tool_calls', None)})"
            for m in msgs
        ]
        logger.info(
            f"🔍 [AGENT:RESULT] keys={list(result.keys())} | structured_response={repr(result.get('structured_response'))} | messages={msgs_summary}"
        )

        image_base64 = result.get("image_base64")
        structured_resp = result.get("structured_response")

        # 1. Se structured_response veio na raiz do state retornado
        if isinstance(structured_resp, AssistantResponse):
            if image_base64 and not structured_resp.image_base64:
                structured_resp.image_base64 = image_base64
            logger.info(
                f"🎯 [AGENT:EXTRACT] structured_response extraído diretamente do state: {structured_resp}"
            )
            return structured_resp
        elif isinstance(structured_resp, dict):
            resp = AssistantResponse(**structured_resp)
            if image_base64 and not resp.image_base64:
                resp.image_base64 = image_base64
            logger.info(f"🎯 [AGENT:EXTRACT] structured_response dict convertido: {resp}")
            return resp

        # 2. Resiliência: se o tool call de AssistantResponse estiver nas mensagens
        for m in reversed(msgs):
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
                for tc in m.tool_calls:
                    if tc.get("name") == "AssistantResponse":
                        args = tc.get("args") or {}
                        resp = AssistantResponse(**args)
                        if image_base64 and not resp.image_base64:
                            resp.image_base64 = image_base64
                        logger.info(f"🎯 [AGENT:EXTRACT] Extraído de AIMessage.tool_calls: {resp}")
                        return resp

        # 3. Fallback: Se o modelo respondeu com texto comum
        last_msg = msgs[-1] if msgs else None
        response_text = (
            str(last_msg.content)
            if last_msg and last_msg.content
            else "Desculpe, não consegui processar sua mensagem."
        )
        logger.warning(
            f"⚠️ [AGENT:FALLBACK] Nenhuma structured_response encontrada. Usando texto da última mensagem: {repr(response_text)}"
        )

        return AssistantResponse(
            response_message=response_text,
            suggested_options=None,
            image_base64=image_base64,
            is_complete=False,
        )
