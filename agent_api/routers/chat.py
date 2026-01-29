import httpx
from fastapi import APIRouter, Depends, HTTPException

from agent_api.core.http_client import get_http_client
from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.dtos import ChatMessage, ChatRequest, ChatResponse
from agent_api.services.backend import BackendService
from agent_api.services.llm import get_llm_response

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest, client: httpx.AsyncClient = Depends(get_http_client)
):
    # Prepare history for LLM
    history_dicts = [h.model_dump() for h in request.history]
    history_dicts.append({"role": "user", "content": request.message})

    try:
        response: AssistantResponse = await get_llm_response(history_dicts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no Agente LLM: {str(e)}")

    final_response_text = response.response_message

    # TO DO: Refactor. The error handling is not ideal and the experience to user is not optimal.
    # Consider using a more robust error handling mechanism and providing a better user experience.

    if response.is_complete:
        backend_service = BackendService(response, client)
        try:
            await backend_service.register()
        except httpx.RequestError as e:
            final_response_text += (
                f"\n\n[Sistema: Erro de conexão com API ao salvar registro: {e}]"
            )
        except httpx.HTTPStatusError as e:
            final_response_text += (
                f"\n\n[Sistema: Erro na API ao salvar registro: {e.response.text}]"
            )
        except Exception as e:
            final_response_text += f"\n\n[Sistema: Houve um erro ao salvar o registro no banco de dados: {str(e)}]"

    # TO DO: Refactor. Think about an efficiente way to bring history to context every request.
    new_history = request.history.copy()
    new_history.append(ChatMessage(role="user", content=request.message))
    new_history.append(ChatMessage(role="assistant", content=final_response_text))

    return ChatResponse(response=final_response_text, history=new_history)
