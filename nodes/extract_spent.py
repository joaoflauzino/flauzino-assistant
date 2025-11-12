from langchain_core.prompts import PromptTemplate
from utils.config import model_name
from langchain_google_genai import ChatGoogleGenerativeAI
from schema import GraphState
from pydantic import BaseModel, ValidationError
import json

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


def extract_entity_from_spent(state: GraphState) -> dict:

    question = state.get("question", "")
    chat_history = state.get("chat_history", [])

    prompt_check = """
    ## Instruções (LEIA COM ATENÇÃO)
    Você é um assistente financeiro da Família Flauzino.
    O usuário fala sobre registros de gastos.

    Considere o histórico da conversa para entender o contexto:
    {chat_history}

    EXTRAIA somente as seguintes chaves (sempre presentes no JSON):
    - categoria
    - valor
    - metodo_pagamento
    - local_compra

    RETORNE APENAS UM JSON VÁLIDO contendo essas chaves e seus valores.
    NÃO inclua texto explicativo, não inclua blocos de código (```), não inclua backticks,
    não adicione comentários, não retorne múltiplos candidatos — apenas o JSON bruto.

    Exemplo de JSON válido:
    {example_spent}

    Caso faltar alguma informação, diga explicitamente:
    'Preciso que você me diga [campo que falta].'

    Exemplos de perguntas incompletas:
    - 'Gastei 50 reais.' -> Preciso que você me diga metodo_pagamento, local_compra e categoria.
    - 'Comprei no mercado com o cartão do itau.' -> Preciso que você me diga valor e categoria.
    - 'Gastei 200 reais no shopping com o cartão do c6 na categoria roupas.' -> Preciso que você me diga local_compra.

    Em hipótese alguma retorne uma resposta vazia ou nula.

    Fala do usuário: {question}
    """
    llm_plain = ChatGoogleGenerativeAI(model=model_name, temperature=0, max_output_tokens=1024)

    prompt = PromptTemplate.from_template(prompt_check).format(
        question=question,
        example_spent=json.dumps(example_spent),
        chat_history=json.dumps(chat_history),
    )

    response = llm_plain.invoke(prompt, json_output=True)

    if state.get("entry_point") != "check":
        chat_history.append({"role": "user", "content": question})

    try:
        response_json = json.loads(response.content)
        spent_entity = SpentEntity(**response_json)
        state["chat_history"].append({"role": "system", "content": spent_entity.model_dump_json()})
        return {**state, "spent": spent_entity, "status": "ok", "awaiting_user_for_spent": False, "last_node": "extract_spent"}
    except (json.JSONDecodeError, ValidationError):
        state["chat_history"].append({"role": "system", "content": response.content})
        return {**state, "spent": response.content, "status": "incomplete", "awaiting_user_for_spent": True, "last_node": "extract_spent"}