import httpx
from fastapi import APIRouter, Depends

from agent_api.core.http_client import get_http_client
from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.dtos import ChatMessage, ChatRequest, ChatResponse
from agent_api.services.finance import FinanceService
from agent_api.services.llm import get_llm_response

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest, client: httpx.AsyncClient = Depends(get_http_client)
):
    history_dicts = [h.model_dump() for h in request.history]
    history_dicts.append({"role": "user", "content": request.message})

    response: AssistantResponse = await get_llm_response(history_dicts)

    final_response_text = response.response_message

    if response.is_complete:
        finance_service = FinanceService(response, client)
        await finance_service.register()

    new_history = request.history.copy()
    new_history.append(ChatMessage(role="user", content=request.message))
    new_history.append(ChatMessage(role="assistant", content=final_response_text))

    return ChatResponse(response=final_response_text, history=new_history)
