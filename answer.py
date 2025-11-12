import os

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from schema import GraphState
from nodes.spent_node import check_conversation_type
from nodes.extract_spent import extract_entity_from_spent
from nodes.normal_conversation import normal_conversation
from decision.decision_node import decision_node, route_decision, entry_router, entry_router_decision

os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

workflow = StateGraph(GraphState)

workflow.add_node("entry_router", entry_router)
workflow.add_node("check", check_conversation_type)
workflow.add_node("decision", decision_node)
workflow.add_node("extract_spent", extract_entity_from_spent)
workflow.add_node("normal_conversation", normal_conversation)

workflow.set_entry_point("entry_router")

workflow.add_conditional_edges(
    "entry_router",
    entry_router_decision,
    {
        "extract_spent": "extract_spent",
        "check": "check",
        END: END,
    },
)


workflow.add_edge("check", "decision")

workflow.add_conditional_edges(
    "decision",
    route_decision,
    {
        "extract_spent": "extract_spent",
        "normal_conversation": "normal_conversation",
        END: END,
    },
)

workflow.add_edge("extract_spent", END)
workflow.add_edge("normal_conversation", END)

memory = MemorySaver()

app = workflow.compile(checkpointer=memory)

conversation_id = "user_234"

while True:
    user_input = input("Você: ")
    if user_input.lower() in ["sair", "exit", "quit"]:
        break
    response = app.invoke(
        {"question": user_input},
        config={"configurable": {"thread_id": conversation_id}},
    )

    print("Assistente:", response.get("spent", None))

    print("Conversa que o assistente teve acess:\n\n")

    for msg in response.get("chat_history", []):
        print(msg)