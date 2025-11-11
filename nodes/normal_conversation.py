from schema import GraphState

def normal_conversation(state: GraphState) -> dict:
    return {
        "response": "Desculpe, estou autorizado a ajudar apenas com finanças pessoais no momento.",
        "status": "ok"
    }