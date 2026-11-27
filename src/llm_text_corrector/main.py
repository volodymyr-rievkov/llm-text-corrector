"""One ASGI app: the API under /api and the Gradio page at /. Run: `uvicorn llm_text_corrector.main:app`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import gradio as gr
import httpx
from fastapi import FastAPI

from llm_text_corrector.backend.api.app import create_api
from llm_text_corrector.frontend.client import BackendClient
from llm_text_corrector.frontend.config import get_frontend_settings
from llm_text_corrector.frontend.ui import build_ui

# Placeholder host for in-process calls; the ASGI transport ignores it.
IN_PROCESS_BACKEND_URL = "http://in-process"


def _close_on_shutdown(app: FastAPI, http: httpx.AsyncClient) -> None:
    """Close `http` when the app's lifespan ends."""
    inner = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(scope: FastAPI) -> AsyncIterator[Any]:
        try:
            async with inner(scope) as state:
                yield state
        finally:
            await http.aclose()

    app.router.lifespan_context = lifespan


def create_app() -> FastAPI:
    settings = get_frontend_settings()
    api = create_api()
    if settings.backend_url is None:
        http = httpx.AsyncClient(transport=httpx.ASGITransport(app=api))
        backend_url = IN_PROCESS_BACKEND_URL
    else:
        http = httpx.AsyncClient()
        backend_url = settings.backend_url
    _close_on_shutdown(api, http)
    client = BackendClient(backend_url, settings.request_timeout_s, http)
    mounted: FastAPI = gr.mount_gradio_app(api, build_ui(client), path="/")
    return mounted


app = create_app()
