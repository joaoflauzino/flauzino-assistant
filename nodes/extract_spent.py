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
    prompt_check = """
    ## Instruções (LEIA COM ATENÇÃO)
    Você é um assistente financeiro da Família Flauzino.
    O usuário fala sobre registros de gastos.

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

    Caso faltar alguma informacão, PERGUNTE para o usuário.

    Fala do usuário: {question}
    """
    llm_plain = ChatGoogleGenerativeAI(model=model_name, temperature=0, max_output_tokens=1024)

    question = state.get("question", "")
    prompt = PromptTemplate.from_template(prompt_check).format(question=question, example_spent=json.dumps(example_spent))

    response = llm_plain.invoke(prompt, json_output=True)

    try:
        response_json = json.loads(response.content)
        spent_entity = SpentEntity(**response_json)
        return {**state, "spent": spent_entity, "status": "ok", "awaiting_user_for_spent": False}
    except (json.JSONDecodeError, ValidationError):
        return {**state, "spent": response.content, "status": "incomplete", "awaiting_user_for_spent": True}