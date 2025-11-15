from langchain_core.prompts import PromptTemplate
from utils.config import model_name
from langchain_google_genai import ChatGoogleGenerativeAI
from schema import GraphState
from pydantic import BaseModel, ValidationError
import json


## TO DO:
## - Tratar retorno de entry point quando for necessário entrar direto nesse nó
## - Quando não á reasoning, a LLM retorna o response vazio
## - Melhorar prompts para extrair as entidades corretamente
## - Avaliar se não é melhor utilizar outro provider

class SpentEntity(BaseModel):
    categoria: str
    valor: float
    metodo_pagamento: str
    local_compra: str
    reasoning: str | None = None


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

    > APENAS preencha o campo `reasoning` caso falte informacoes na fala do usuário. Caso isso aconteca, elabore uma pergunta para obter os dados faltantes.
    > Se alguma informação estiver faltando na fala do usuário, coloque null no respectivo campo.

    ---------------------------------------------------------------------------
    2. RETORNO DO JSON
    ---------------------------------------------------------------------------

    > RETORNE UM JSON VÁLIDO!

    >> Exemplo de JSON válido:
        {example_spent}

    > IMPORTANTE: Se alguma informação estiver faltando na fala do usuário, peça educadamente para que ele forneça os dados faltantes.

    >> Exemplos de perguntas incompletas:
        - 'Gastei 50 reais.' -> Preciso que você me diga metodo_pagamento, local_compra e categoria.
        - 'Comprei no mercado com o cartão do itau.' -> Preciso que você me diga valor e categoria.
        - 'Gastei 200 reais no shopping com o cartão do c6 na categoria roupas.' -> Preciso que você me diga local_compra.

    Fala do usuário: {question}
    """
    llm_plain = ChatGoogleGenerativeAI(model=model_name, temperature=0) \
                .with_structured_output(SpentEntity, include_raw=True)

    prompt = PromptTemplate.from_template(prompt_check).format(
        question=question,
        example_spent=json.dumps(example_spent),
        chat_history=json.dumps(chat_history),
    )


    if state.get("entry_point") != "check":
        chat_history.append({"role": "user", "content": question})


    try:
        response = llm_plain.invoke(prompt)
        return {**state, "spent": response.get("parsed", None), "raw": response.get("raw", None), "status": "ok", "awaiting_user_for_spent": False, "last_node": "extract_spent"}
    except Exception as e:
        chat_history.append({"role": "system", "content": str(e)})
        return {**state, "spent": None, "error": str(e), "status": "incomplete", "awaiting_user_for_spent": True, "last_node": "extract_spent"}