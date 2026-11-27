"""The two HTTP endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from llm_text_corrector.backend.api.deps import get_api_key, get_service
from llm_text_corrector.backend.api.schemas import CorrectionBody, CorrectionResponse, ErrorResponse, HealthResponse
from llm_text_corrector.backend.domain.models import CorrectionRequest
from llm_text_corrector.backend.service import CorrectionService

router = APIRouter()

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorResponse} for status in (401, 422, 429, 502, 504)
}


@router.post("/api/v1/corrections", response_model=CorrectionResponse, responses=_ERROR_RESPONSES)
async def correct_text(
    body: CorrectionBody,
    service: Annotated[CorrectionService, Depends(get_service)],
    api_key: Annotated[str, Depends(get_api_key)],
) -> CorrectionResponse:
    result = await service.correct(CorrectionRequest(text=body.text), api_key=api_key)
    return CorrectionResponse(corrected_text=result.corrected_text)


@router.get("/api/health")
async def health() -> HealthResponse:
    return HealthResponse()
