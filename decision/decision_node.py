from schema import GraphState
from langgraph.graph import END

def entry_router(state: GraphState) -> GraphState:
    """Define se o grafo deve retomar do último nó ou seguir o fluxo padrão."""
    print("[entry_router] Verificando último nó e estado pendente...")

    if state.get("awaiting_user_for_spent") and state.get("last_node") == "extract_spent":
        print("[entry_router] Retomando do nó 'extract_spent'")
        state["entry_point"] = "extract_spent"
    else:
        print("[entry_router] Fluxo normal -> nó 'check'")
        state["entry_point"] = "check"
    return state


def entry_router_decision(state: GraphState):
    """Roteia para o nó de entrada definido."""
    print(f"[entry_router_decision] Roteando para: {state.get('entry_point')}")
    return state.get("entry_point", END)


def decision_node(state: GraphState) -> GraphState:
    """Define o próximo nó com base no tipo da conversa."""
    print(f"[decision] Tipo detectado: {state.get('type')}")

    if state.get("type") == "REGISTRO":
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