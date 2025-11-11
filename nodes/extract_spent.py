from langchain_core.prompts import PromptTemplate
from utils.config import model_name
from langchain_google_genai import ChatGoogleGenerativeAI
from schema import GraphState
from pydantic import BaseModel, ValidationError

class SpentEntity(BaseModel):
    categoria: str
    valor: str
    metodo_pagamento: str
    local_compra: str

def extract_entity_from_spent(state: GraphState) -> dict:
    prompt_check = """    
    ## Instruções
    Você é um assistente financeiro da Família Flauzino.
    O usuário fala sobre registros de gastos.
    Extraia as seguintes informações:

    - Categoria do gasto
    - Valor do gasto
    - Método de pagamento
    - Local da compra

    Caso alguma dessas informações falte, informe o usuário que está faltando essa informação e que precisa dela para identificar o gasto.
    Apenas responda a pergunta necessária, de forma natural e curta.

    Fala do usuário: {question}
    """

    llm_struct = ChatGoogleGenerativeAI(model=model_name).with_structured_output(SpentEntity)
    llm_plain = ChatGoogleGenerativeAI(model=model_name)

    question = state.get("question", "")
    prompt = PromptTemplate.from_template(prompt_check).format(question=question)

    response = llm_plain.invoke(prompt)

    return {**state, "spent": response, "status": "ok"}
