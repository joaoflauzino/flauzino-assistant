from langchain_core.prompts import PromptTemplate
from utils.config import model_name
from langchain_google_genai import ChatGoogleGenerativeAI
from schema import GraphState
from pydantic import BaseModel
import json


## TO DO:
## - Tratar retorno de entry point quando for necessário entrar direto nesse nó -> ok
## - LLM continua retornando vazio em casos com max_tokens baixos ->
## - Implementar tratativa para quando o response for igual a None e avaliar quando isso acontece ->
## - Melhorar prompts para extrair as entidades corretamente -> ok
## - Avaliar se não é melhor utilizar outro provider -> ok
## - Realizar alteração e utilizar como na doc (https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai) -> ok

class SpentEntity(BaseModel):
    categoria: str
    valor: float
    metodo_pagamento: str
    local_compra: str

example_spent = {
    'categoria': 'comer fora',
    'valor': 100,
    'metodo_pagamento': 'cartao de crédito do c6',
    'local_compra': 'punch'
}

def _check_spent_entity(spent: SpentEntity) -> list:
    missing_data = []
    required_keys = ['categoria', 'valor', 'metodo_pagamento', 'local_compra']
    spent_dict = spent.model_dump()
    for key in required_keys:
        if spent_dict[key] == "null":
            missing_data.append(key)
    return missing_data

async def extract_entity_from_spent(state: GraphState) -> dict:

    question = state.get("question", "")
    chat_history = state.get("chat_history", [])

    prompt_check = """

    ---------------------------------------------------------------------------
    # INSTRUCÕES
    ---------------------------------------------------------------------------

    Você é um assistente financeiro da Família Flauzino.
    O usuário fala sobre registros de gastos.
    Seu objetivo é extrair as informações relevantes sobre o gasto mencionado pelo usuário.

    Considere o histórico da conversa para entender o contexto:
    {chat_history}

    ---------------------------------------------------------------------------
    1. EXTRACÃO DE ENTIDADES
    ---------------------------------------------------------------------------

    > EXTRAIA somente as seguintes chaves (sempre presentes no JSON):
        - categoria
        - valor
        - metodo_pagamento
        - local_compra

    ---------------------------------------------------------------------------
    2. RETORNO DO JSON
    ---------------------------------------------------------------------------

    > RETORNE UM JSON VÁLIDO!

    >> Exemplo de JSON válido:
        {example_spent}

    > IMPORTANTE: Se alguma informação estiver faltando na fala do usuário, peça educadamente para que ele forneça os dados faltantes.
    > APENAS preencha o campo `reasoning` caso falte informacoes na fala do usuário. Caso isso aconteca, elabore uma pergunta para obter os dados faltantes.
    > Se alguma informação estiver faltando na fala do usuário, coloque null no respectivo campo.

    >> Exemplos de perguntas incompletas:
        - 'Gastei 50 reais.' -> Preciso que você me diga metodo_pagamento, local_compra e categoria.
        - 'Comprei no mercado com o cartão do itau.' -> Preciso que você me diga valor e categoria.
        - 'Gastei 200 reais no shopping com o cartão do c6 na categoria roupas.' -> Preciso que você me diga local_compra.

    Fala do usuário: {question}
    """
    llm_plain = ChatGoogleGenerativeAI(model=model_name, temperature=0, max_tokens=1024) \
                .with_structured_output(SpentEntity)

    prompt = PromptTemplate.from_template(prompt_check).format(
        question=question,
        example_spent=json.dumps(example_spent),
        chat_history=json.dumps(chat_history),
    )

    if state.get("entry_point") != "check":
        chat_history.append({"role": "user", "content": question})

    response = await llm_plain.ainvoke(prompt)
    missing_data = _check_spent_entity(response)

    if not missing_data:
        return {**state, "spent": response, "status": "ok", "awaiting_user_for_spent": False, "last_node": "extract_spent"}

    msg = f"Está faltando as seguintes informações para registrar o gasto: {', '.join(missing_data)}. Por favor, forneça esses dados."
    chat_history.append({"role": "system", "content": msg})
    return {**state, "spent": msg, "status": "incomplete", "awaiting_user_for_spent": True, "last_node": "extract_spent"}