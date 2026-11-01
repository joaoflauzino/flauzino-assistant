from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    platform: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    history: list[ChatMessage]
    is_complete: bool = False
    suggested_options: list[str] | None = None
    image_base64: str | None = None
