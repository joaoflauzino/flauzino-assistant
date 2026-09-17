import httpx
from fastapi import Depends
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from agent_api.core.database import get_db
from agent_api.core.http_client import get_http_client
from agent_api.core.llm import get_llm
from agent_api.services.agent import AgentService
from agent_api.services.chat import ChatService
from agent_api.services.finance import FinanceService
from agent_api.services.graph import GraphService


def get_agent_service(
    client: httpx.AsyncClient = Depends(get_http_client),
    llm: BaseChatModel = Depends(get_llm),
) -> AgentService:
    finance_service = FinanceService(client=client)
    graph_service = GraphService(client=client)
    return AgentService(llm, finance_service, graph_service)


def get_chat_service(
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
) -> ChatService:
    return ChatService(db, agent_service)
