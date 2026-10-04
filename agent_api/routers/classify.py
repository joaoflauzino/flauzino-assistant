from fastapi import APIRouter, Depends

from agent_api.core.logger import get_logger
from agent_api.dependencies import get_classify_service
from agent_api.schemas.classify import ClassifyBatchRequest, ClassifyBatchResponse
from agent_api.services.classify import ClassifyService

logger = get_logger(__name__)

router = APIRouter(prefix="/classify", tags=["Classify"])


@router.post("/transactions", response_model=ClassifyBatchResponse)
async def classify_transactions(
    request: ClassifyBatchRequest,
    service: ClassifyService = Depends(get_classify_service),
):
    """Classifica um lote de transações em categorias válidas usando LLM."""
    logger.info(f"Received classification request for {len(request.transactions)} transactions")
    return await service.classify_transactions(request)
