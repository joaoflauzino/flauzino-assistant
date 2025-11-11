import os
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from schema import GraphState
from nodes.spent_node import check_conversation_type
from nodes.extract_spent import extract_entity_from_spent
from nodes.extract_budget import extract_entity_from_budget
from nodes.normal_conversation import normal_conversation
from decision.decision_node import decision_node, route_decision

os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

memory = MemorySaver()

workflow = StateGraph(GraphState)

workflow.add_node("check", check_conversation_type)
workflow.add_node("decision", decision_node)
workflow.add_node("extract_spent", extract_entity_from_spent)
workflow.add_node("extract_budget", extract_entity_from_budget)
workflow.add_node("normal_conversation", normal_conversation)

workflow.set_entry_point("check")

workflow.add_edge("check", "decision")

workflow.add_conditional_edges(
    "decision",
    route_decision,
    {
        "extract_spent": "extract_spent",
        "extract_budget": "extract_budget",
        "normal_conversation": "normal_conversation",
        END: END,
    },
)


workflow.add_conditional_edges(
    "extract_spent",
    lambda s: END if s.get("status") == "ok" else "extract_spent",
    {END: END, "extract_spent": "extract_spent"},
)

workflow.add_edge("extract_budget", END)
workflow.add_edge("normal_conversation", END)


app = workflow.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "thread-1"}}
state = {"question": "Gastei 100 reais."}

for event in app.stream(state, config):
    for value in event.values():
        print(value)