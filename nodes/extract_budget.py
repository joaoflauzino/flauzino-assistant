from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from schema import GraphState
from pydantic import BaseModel, ValidationError
from utils.config import model_name

class BudgetEntity(BaseModel):
    categoria: str
    valor: str
    
def extract_entity_from_budget(state: GraphState) -> dict:
    prompt_check = """    
    
    ## Instruções
    Você é um especialista e assistente de finanças da Família Flauzino. A sua responsabilidade é identificar
    entidades em uma conversa de finanças pessoais. O usuário estará falando sobre limite de gastos. 
    Você precisará extrair as seguintes informações:

    - Categoria do gasto (ex: mercado, comer fora, transporte, lazer, etc)
    - Valor do gasto (ex: 100 reais)

    Caso não houver todas essas informações na fala do usuário, pergunte de volta para o usuário para obter as informações faltantes.

    Você precisa retornar as informações no seguinte formato JSON:

    categoria: categoria do gasto
    valor: valor do gasto
    

    ## Exemplos

    - Entrada: 'Olá, eu quero criar uma nova categoria de limite de gastos para "farmacia" de 200 reais'
      Saída:
      
        categoria: farmacia
        valor: 200 reais

    - Entrada: 'Quero criar uma categoria de "emergencias" no valor de 300 reais'
      Saída:

        categoria: emergencias
        valor: 300 reais

    - Entrada: 'Quero criar uma categoria de "roupas" no valor de 100 reais'
      Saída:

        categoria: roupas
        valor: 100 reais

    Fala do usuário: {question}

    """
    

    llm = ChatGoogleGenerativeAI(model=model_name)
    llm_with_structured = llm.with_structured_output(BudgetEntity)
    llm_plain = ChatGoogleGenerativeAI(model=model_name)

    prompt_template = PromptTemplate(
        input_variables=['question'],
        template=prompt_check.strip(), 
    )

    question: str = state['question']

    final_prompt = prompt_template.format(question=question)

    try:
        response: BudgetEntity = llm_with_structured.invoke(final_prompt)
        return {**state, "budget": response.model_dump(), "status": "ok"}
    except ValidationError:
      followup = llm_plain.invoke(final_prompt)
      return {**state, "follow_up": followup.content, "status": "incomplete"}