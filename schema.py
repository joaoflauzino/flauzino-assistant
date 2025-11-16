from typing import TypedDict
from pydantic import BaseModel

class GraphState(TypedDict):
    next_node: str
    question: str
    type: dict 
    response: dict
    raw: dict 
    spent: BaseModel | str
    budget: dict
    status: str
    awaiting_user_for_spent: bool
    last_node: str
    entry_point: str
    chat_history: list
    error: str