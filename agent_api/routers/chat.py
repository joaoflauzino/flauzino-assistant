from fastapi import APIRouter, Depends

from agent_api.dependencies import get_chat_service
from agent_api.schemas.dtos import ChatRequest, ChatResponse
from agent_api.services.chat import ChatService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    return await service.process_message(request.message, request.session_id, request.platform)
