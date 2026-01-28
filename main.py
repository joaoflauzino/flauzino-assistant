import asyncio

from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import settings
from schemas.assistant import AssistantResponse

SYSTEM_PROMPT = """
Você é um assistente financeiro da Família Flauzino.
Seu objetivo é:

    - cadastrar limites de gastos
    - ajudar a registrar gastos

1. **Registro de Gastos**:
   Se o usuário estiver tentando registrar um gasto, você deve extrair as seguintes informações:
   - `categoria`
   - `valor`
   - `metodo_pagamento`
   - `local_compra`

   - Se alguma informação estiver faltando, sua `response_message` deve perguntar educadamente especificamente pelos dados que faltam.
   - Se todas as informações estiverem presentes, sua `response_message` deve confirmar o registro com os dados extraídos.
   - Marque `is_complete` como True apenas se tiver todos os 4 campos.

2. **Cadastro de Limites de Gastos**:
   Se o usuário estiver tentando cadastrar um limite de gastos, você deve extrair as seguintes informações:
   - `categoria`
   - `valor`

   - Se alguma informação estiver faltando, sua `response_message` deve perguntar educadamente especificamente pelos dados que faltam.
   - Se todas as informações estiverem presentes, sua `response_message` deve confirmar o registro com os dados extraídos.
   - Marque `is_complete` como True apenas se tiver todos os 2 campos.

3. **Outros Assuntos**:
   Se o usuário falar sobre assuntos que NÃO sejam finanças ou registro de gastos, sua `response_message` deve ser:
   "Desculpe, estou autorizado a ajudar apenas com finanças pessoais no momento."
   E `spending_details` deve ser null.

4. **Histórico**:
   Use o histórico da conversa para entender correções ou adições de informações anteriores (ex: se o usuário disse o valor antes e agora disse o local).
"""


async def get_response(history: list) -> AssistantResponse:
    llm = ChatGoogleGenerativeAI(
        model=settings.MODEL_NAME, temperature=0
    ).with_structured_output(AssistantResponse)

    messages = [("system", SYSTEM_PROMPT)]
    for msg in history:
        role = "human" if msg["role"] == "user" else "ai"
        messages.append((role, msg["content"]))

    response = await llm.ainvoke(messages)
    return response


async def main():
    print("Iniciando assistente financeiro (Single Prompt)...")
    chat_history = []

    while True:
        try:
            user_input = input("Você: ")
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break

        if not user_input.strip():
            continue

        if user_input.lower() in ["sair", "exit", "quit"]:
            break

        chat_history.append({"role": "user", "content": user_input})

        try:
            response: AssistantResponse = await get_response(chat_history)

            print(f"Assistente: {response.response_message}")

            if response.spending_details and response.is_complete:
                print(
                    f"\n[DEBUG] Gasto completo detectado: {response.spending_details.model_dump()}\n"
                )

            if response.limit_details and response.is_complete:
                print(
                    f"\n[DEBUG] Gasto completo detectado: {response.limit_details.model_dump()}\n"
                )

            # Adiciona a resposta ao histórico para manter o contexto
            chat_history.append(
                {"role": "assistant", "content": response.response_message}
            )

        except Exception as e:
            print(f"Erro ao processar: {e}")


if __name__ == "__main__":
    asyncio.run(main())
