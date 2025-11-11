from schema import GraphState
from langgraph.graph import END

def decision_node(state: GraphState) -> GraphState:
    """Define o próximo nó com base no tipo da conversa."""
    print(f"[decision] Tipo detectado: {state.get('type')}")

    if state.get("awaiting_user_for_spent"):
        state["next_node"] = "extract_spent"
    elif state.get("type") == "REGISTRO":
        state["next_node"] = "extract_spent"
    elif state.get("type") == "OUTROS":
        state["next_node"] = "normal_conversation"
    else:
        state["next_node"] = END

    print(f"[decision] Próximo nó definido: {state['next_node']}")
    return state


def route_decision(state: GraphState):
    """Define qual será o próximo nó com base no campo next_node."""
    print(f"[route_decision] Próximo nó: {state.get('next_node')}")
    return state.get("next_node", END)