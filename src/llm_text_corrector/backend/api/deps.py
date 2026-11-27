"""FastAPI dependency providers; override them in tests via `app.dependency_overrides`."""

from typing import Annotated

import httpx
from fastapi import Depends, Header, Request

from llm_text_corrector.backend.config import Settings, get_settings
from llm_text_corrector.backend.llm.client import LLMClient
from llm_text_corrector.backend.llm.groq import GroqClient
from llm_text_corrector.backend.service import CorrectionService


def get_http_client(request: Request) -> httpx.AsyncClient:
    client: httpx.AsyncClient = request.app.state.http_client
    return client


def get_llm_client(
    settings: Annotated[Settings, Depends(get_settings)],
    http: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> LLMClient:
    return GroqClient(
        http,
        base_url=settings.groq_base_url,
        model=settings.model,
        timeout=settings.timeout_s,
        reasoning_effort=settings.reasoning_effort,
    )


def get_service(
    settings: Annotated[Settings, Depends(get_settings)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> CorrectionService:
    return CorrectionService(llm, max_input_chars=settings.max_input_chars)


def get_api_key(x_groq_api_key: Annotated[str | None, Header()] = None) -> str:
    """A missing header becomes a blank key, which the service rejects as `missing_api_key`."""
    return (x_groq_api_key or "").strip()
