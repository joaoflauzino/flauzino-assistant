import httpx
from langchain_google_genai import ChatGoogleGenerativeAI

from agent_api.core.decorators import handle_llm_errors
from agent_api.core.logger import get_logger
from agent_api.schemas.assistant import AssistantResponse
from agent_api.settings import settings

logger = get_logger(__name__)


# Fetch categories dynamically from finance API
async def get_valid_categories() -> str:
    """Fetch valid categories from finance API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.FINANCE_SERVICE_URL}/categories?size=100")
            if response.status_code == 200:
                data = response.json()
                categories = [item["key"] for item in data.get("items", [])]
                return ", ".join(categories)
    except Exception as e:
        logger.warning(f"Failed to fetch categories: {e}")
    # Fallback to common categories
    return "alimentacao, comer_fora, farmacia, mercado, transporte, moradia, saude, lazer, educação, compras, vestuario, viagem, serviços, crianças, outros"


async def get_valid_payment_methods() -> str:
    """Fetch valid payment methods from finance API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.FINANCE_SERVICE_URL}/payment-methods?size=100")
            if response.status_code == 200:
                data = response.json()
                methods = [item["key"] for item in data.get("items", [])]
                return ", ".join(methods)
    except Exception as e:
        logger.warning(f"Failed to fetch payment methods: {e}")
    return "itau, nubank, picpay, xp, c6, pix"


async def get_valid_owners() -> str:
    """Fetch valid payment owners from finance API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.FINANCE_SERVICE_URL}/payment-owners?size=100")
            if response.status_code == 200:
                data = response.json()
                owners = [item["key"] for item in data.get("items", [])]
                return ", ".join(owners)
    except Exception as e:
        logger.warning(f"Failed to fetch payment owners: {e}")
    return "joao_lucas, lailla"


async def get_system_prompt(platform: str | None = None) -> str:
    """Generate system prompt with dynamic categories and platform instructions."""
    valid_categories = await get_valid_categories()
    valid_payment_methods = await get_valid_payment_methods()
    valid_owners = await get_valid_owners()

    platform_instructions = ""
    if platform == "telegram":
        platform_instructions = (
            "**Formatação para Telegram**:\n"
            "O usuário está conversando pelo Telegram. Você DEVE formatar o texto para ficar visualmente agradável.\n"
            "- Use emojis relevantes com moderação para tornar a conversa leve.\n"
            "- Para dar ênfase (negrito), use UM ÚNICO asterisco (*palavra* ou *frase*). NUNCA use dois asteriscos ou underscores e nunca use tags HTML!\n"
            "- Seja direto, conciso, e muito educado, como um assistente de classe mundial.\n"
            "- Nunca envie blocos de texto muito extensos a não ser que o usuário peça."
        )
    elif platform == "web":
        platform_instructions = (
            "**Formatação para Web**:\n"
            "O usuário está usando o sistema Web. Evite o uso excessivo de emojis.\n"
            "- Mantenha uma resposta limpa, direta e formal-objetiva."
        )

    return f"""
        Você é um assistente financeiro da Família Flauzino.
        Seu objetivo é:

            - cadastrar limites de gastos
            - ajudar a registrar gastos

        **CATEGORIAS VÁLIDAS**:
        O campo `categoria` DEVE ser estritamente um destes valores:
        [{valid_categories}]

        **MÉTODOS DE PAGAMENTO VÁLIDOS**:
        O campo `metodo_pagamento` DEVE ser estritamente um destes valores:
        [{valid_payment_methods}]

        **NOMES DE PROPRIETÁRIOS VÁLIDOS**:
        O campo `proprietario` DEVE ser estritamente um destes valores:
        [{valid_owners}]

        1. **Registro de Gastos**:
        Se o usuário estiver tentando registrar um gasto, você deve extrair as seguintes informações:
        - `categoria` (Deve ser uma das categorias válidas acima)
        - `item_comprado`
        - `valor`
        - `metodo_pagamento`
        - `proprietario`
        - `local_compra`

        - Se alguma informação estiver faltando, sua `response_message` deve perguntar educadamente especificamente pelos dados que faltam.
          **IMPORTANTE:** Quando perguntar por múltiplos itens que faltam, ou confirmar múltiplos itens, faça isso OBRIGATORIAMENTE em formato de lista com hífens (-). NUNCA USE tags HTML como <ul> ou <li> para fazer listas.
          Exemplo:
          Por favor, me diga:
          - qual a categoria do gasto
          - item comprado
          - valor
        - Se todas as informações estiverem presentes, sua `response_message` deve confirmar o registro com todos os dados extraídos, também usando lista com hífens (nunca tags html).
        - Marque `is_complete` como True apenas se tiver todos os 4 campos preenchidos corretamente.
        - Confirme com o usuário se os dados estão corretos usando uma lista clara e após confirmação marque `is_confirmed` como True.

        2. **Cadastro de Limites de Gastos**:
        Se o usuário estiver tentando cadastrar um limite de gastos, você deve extrair as seguintes informações:
        - `categoria` (Deve ser uma das categorias válidas acima)
        - `valor`

        - Se alguma informação estiver faltando, sua `response_message` deve perguntar educadamente especificamente pelos dados que faltam.
        - Se todas as informações estiverem presentes, sua `response_message` deve confirmar o registro com os dados extraídos.
        - Marque `is_complete` como True apenas se tiver todos os 2 campos preenchidos corretamente.
        - Confirme com o usuário se os dados estão corretos e após confirmação marque `is_confirmed` como True.

        3. **Outros Assuntos**:
        Se o usuário falar sobre assuntos que NÃO sejam finanças ou registro de gastos, sua `response_message` deve ser:
        "Desculpe, estou autorizado a ajudar apenas com finanças pessoais no momento."
        E `spending_details` deve ser null.

        4. **Histórico**:
        Use o histórico da conversa para entender correções ou adições de informações anteriores (ex: se o usuário disse o valor antes e agora disse o local).
        
        {platform_instructions}
    """


@handle_llm_errors
async def get_llm_response(history: list, platform: str | None = None) -> AssistantResponse:
    llm = ChatGoogleGenerativeAI(model=settings.MODEL_NAME, temperature=0).with_structured_output(
        AssistantResponse
    )

    logger.info("Calling LLM service")

    system_prompt = await get_system_prompt(platform)
    messages = [("system", system_prompt)]
    for msg in history:
        role = "human" if msg["role"] == "user" else "ai"
        messages.append((role, msg["content"]))

    return await llm.ainvoke(messages)
