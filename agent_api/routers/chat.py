import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent_api.core.database import get_db
from agent_api.core.http_client import get_http_client
from agent_api.schemas.dtos import ChatRequest, ChatResponse
from agent_api.services.chat import ChatService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    service = ChatService(db, client)
    return await service.process_message(request.message, request.session_id)
