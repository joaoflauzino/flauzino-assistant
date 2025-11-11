from typing import TypedDict
class GraphState(TypedDict):
    next_node: str
    question: str
    type: dict 
    response: dict
    spent: dict
    budget: dict
    status: str