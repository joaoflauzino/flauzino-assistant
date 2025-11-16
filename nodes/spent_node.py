from langchain_core.prompts import PromptTemplate
from langchain_core.messages.ai import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from schema import GraphState
from utils.config import model_name

async def check_conversation_type(state: GraphState) -> dict:
    prompt_check = """

    ## Instruções
    Você é um especialista e assistente de finanças da Família Flauzino. A sua responsabilidade é identificar
    se o usuário está falando sobre registros de gastos ou se esta falando sobre outros assuntos.
    - Registro de gastos: Registrar ou consultar gastos para determinadas categorias
    - Outros assuntos: Qualquer outro tópico que não seja registro de gastos.

    Você precisa retornar 2 possibilidades:

        Registro de gastos -> REGISTRO
        Outros tópicos -> OUTROS

    ## Exemplos

    ### Registro de gastos -> REGISTRO
    - Olá, gastei 100 reais no punch com o cartao de crédito do c6 na categoria "comer fora"
    - Comprei 1 coca cola por 11 reais no bar com o cartao do itau na categoria "comer fora"
    - Gastei 500 reais em compras no mercado com o cartao do c6 na categoria "mercado"
    - Gostaria de consultar meus gastos

    ### Outros assuntos -> OUTROS
    - Olá, o que você pode fazer?
    - Me ajude a organizar minha vida financeira
    - Quais são as melhores práticas para economizar dinheiro?

    Fala do usuário: \n{question}

    """

    llm = ChatGoogleGenerativeAI(model=model_name)

    prompt_template = PromptTemplate(
        input_variables=["question"],
        template=prompt_check,
    )

    question: str = state["question"]

    final_prompt = prompt_template.format(question=question)

    response: AIMessage = await llm.ainvoke(final_prompt)

    operation_type = str(response.content).strip()

    state["chat_history"] = [{"role": "user", "content": question}, {"role": "assistant", "content": response.content}]

    return {
        **state,
        "question": state["question"],
        "type": operation_type,
    }
