from typing import Annotated

import httpx
from fastapi import Depends
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from agent_api.core.database import get_db
from agent_api.core.http_client import get_http_client
from agent_api.core.llm import LLMProfile, get_llm
from agent_api.repositories.chat_repository import ChatRepository
from agent_api.repositories.protocols import ChatRepositoryProtocol
from agent_api.services.agent import AgentService
from agent_api.services.audio import AudioService, FasterWhisperTranscriber
from agent_api.services.audio_protocols import AudioServiceProtocol
from agent_api.services.chat import ChatService
from agent_api.services.classify import ClassifyService
from agent_api.services.clients.finance import FinanceService
from agent_api.services.clients.graph import GraphService
from agent_api.services.ocr import OCRService, OpenCVImagePreprocessor, TesseractTextRecognizer
from agent_api.services.ocr_protocols import OCRServiceProtocol
from agent_api.services.receipts import ReceiptService

DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]


def get_chat_llm() -> BaseChatModel:
    return get_llm(LLMProfile.CHAT_AGENT)


def get_classifier_llm() -> BaseChatModel:
    return get_llm(LLMProfile.BATCH_CLASSIFIER)


LLMDep = Annotated[BaseChatModel, Depends(get_chat_llm)]
ClassifierLLMDep = Annotated[BaseChatModel, Depends(get_classifier_llm)]


def get_chat_repository(db: DBSessionDep) -> ChatRepositoryProtocol:
    return ChatRepository(db)


ChatRepoDep = Annotated[ChatRepositoryProtocol, Depends(get_chat_repository)]


def get_agent_service(
    client: HttpClientDep,
    llm: LLMDep,
) -> AgentService:
    finance_service = FinanceService(client=client)
    graph_service = GraphService(client=client)
    return AgentService(llm, finance_service, graph_service)


AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]


def get_chat_service(
    repository: ChatRepoDep,
    agent_service: AgentServiceDep,
) -> ChatService:
    return ChatService(repository, agent_service)


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


def get_audio_service() -> AudioServiceProtocol:
    return AudioService(FasterWhisperTranscriber())


AudioServiceDep = Annotated[AudioServiceProtocol, Depends(get_audio_service)]


def get_ocr_service() -> OCRServiceProtocol:
    return OCRService(
        preprocessor=OpenCVImagePreprocessor(),
        recognizer=TesseractTextRecognizer(),
    )


OCRServiceDep = Annotated[OCRServiceProtocol, Depends(get_ocr_service)]


def get_receipt_service(ocr_service: OCRServiceDep) -> ReceiptService:
    return ReceiptService(ocr_service=ocr_service)


ReceiptServiceDep = Annotated[ReceiptService, Depends(get_receipt_service)]


def get_classify_service(
    llm: ClassifierLLMDep,
) -> ClassifyService:
    return ClassifyService(llm=llm)


ClassifyServiceDep = Annotated[ClassifyService, Depends(get_classify_service)]
