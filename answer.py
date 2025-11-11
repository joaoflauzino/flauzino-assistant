import os
from langgraph.graph import StateGraph, END

from schema import GraphState
from nodes.spent_node import check_conversation_type
from nodes.extract_spent import extract_entity_from_spent
from nodes.normal_conversation import normal_conversation
from decision.decision_node import decision_node, route_decision

os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

workflow = StateGraph(GraphState)

workflow.add_node("check", check_conversation_type)
workflow.add_node("decision", decision_node)
workflow.add_node("extract_spent", extract_entity_from_spent)
workflow.add_node("normal_conversation", normal_conversation)

workflow.set_entry_point("check")

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

app = workflow.compile()

input = {"question": input("Digite sua pergunta: ")}

response = app.invoke(input)
print("Response:", response)