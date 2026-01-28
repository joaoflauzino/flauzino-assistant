import httpx
from fastapi import APIRouter, HTTPException

from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.dtos import ChatMessage, ChatRequest, ChatResponse
from agent_api.services.backend import save_limit, save_spent
from agent_api.services.llm import get_llm_response

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # Prepare history for LLM
    history_dicts = [h.model_dump() for h in request.history]
    history_dicts.append({"role": "user", "content": request.message})

    try:
        response: AssistantResponse = await get_llm_response(history_dicts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no Agente LLM: {str(e)}")

    final_response_text = response.response_message

    if response.is_complete:
        if response.spending_details:
            try:
                await save_spent(response.spending_details)
            except httpx.RequestError as e:
                final_response_text += (
                    f"\n\n[Sistema: Erro de conexão com API ao salvar gasto: {e}]"
                )
            except httpx.HTTPStatusError as e:
                final_response_text += (
                    f"\n\n[Sistema: Erro na API ao salvar gasto: {e.response.text}]"
                )
            except Exception as e:
                final_response_text += f"\n\n[Sistema: Houve um erro ao salvar o registro no banco de dados: {str(e)}]"

        elif response.limit_details:
            try:
                await save_limit(response.limit_details)
            except httpx.RequestError as e:
                final_response_text += (
                    f"\n\n[Sistema: Erro de conexão com API ao salvar limite: {e}]"
                )
            except httpx.HTTPStatusError as e:
                final_response_text += (
                    f"\n\n[Sistema: Erro na API ao salvar limite: {e.response.text}]"
                )
            except Exception as e:
                final_response_text += f"\n\n[Sistema: Houve um erro ao salvar o limite no banco de dados: {str(e)}]"

    # Update history
    new_history = request.history.copy()
    new_history.append(ChatMessage(role="user", content=request.message))
    new_history.append(ChatMessage(role="assistant", content=final_response_text))

    return ChatResponse(response=final_response_text, history=new_history)
