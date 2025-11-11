from langchain_core.prompts import PromptTemplate
from langchain_core.messages.ai import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from schema import GraphState

def check_conversation_type(state: GraphState) -> dict:
    prompt_check = """

    ## Instruções
    Você é um especialista e assistente de finanças da Família Flauzino. A sua responsabilidade é identificar
    se o usuário está falando sobre registros de gastos ou esta apenas falando sobre os limites de gastos.
    - Registro de gastos: Registrar ou consultar gastos para determinadas categorias
    - Limite de gastos: Registrar ou consultar limite de gastos para determinadas categorias

    Você precisa retornar 2 possibilidades:

        Registro de gastos -> REGISTRO
        Limite de gastos -> LIMITE
        Outros tópicos -> OUTROS

    ## Exemplos

    ### Registro de gastos -> REGISTRO
    - Olá, gastei 100 reais no punch com o cartao de crédito do c6 na categoria "comer fora"
    - Comprei 1 coca cola por 11 reais no bar com o cartao do itau na categoria "comer fora"
    - Gastei 500 reais em compras no mercado com o cartao do c6 na categoria "mercado"
    - Gostaria de consultar meus gastos

    ### Consulta de limite de gastos -> LIMITE
    - Olá, gostaria de saber quanto posso gastar na categoria "comer fora"
    - Quero saber meus limites de gastos
    - Gostaria de criar um novo limite de gastos

    Fala do usuário: \n{question}

    """

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite")

    prompt_template = PromptTemplate(
        input_variables=["question"],
        template=prompt_check,
    )

    question: str = state["question"]

    final_prompt = prompt_template.format(question=question)

    response: AIMessage = llm.invoke(final_prompt)

    operation_type = str(response.content).strip()

    return {
        **state,
        "question": state["question"],
        "type": operation_type,
    }
