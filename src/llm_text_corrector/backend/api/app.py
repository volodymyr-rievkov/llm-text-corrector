"""Application factory: `uvicorn llm_text_corrector.backend.api.app:create_api --factory`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from llm_text_corrector.backend.api.errors import register_error_handlers
from llm_text_corrector.backend.api.routes import router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with httpx.AsyncClient() as http_client:
        app.state.http_client = http_client
        yield


def create_api() -> FastAPI:
    app = FastAPI(title="LLM text corrector", lifespan=_lifespan)
    register_error_handlers(app)
    app.include_router(router)
    return app
