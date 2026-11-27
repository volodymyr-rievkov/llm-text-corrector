import json
import socket
import threading
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import httpx
import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

from llm_text_corrector.backend.config import Settings
from llm_text_corrector.backend.llm.groq import GroqClient
from tests.shared.factories.config import SettingsFactory

API_KEY = "gsk_integration_secret"
MODEL = "stub-model"
TIMEOUT_S = 0.3
SLOW_REPLY_MAX_S = 5.0
CHAT_PATH = "/openai/v1/chat/completions"
MAX_CHARS = 40


def chat_body(content: str) -> dict[str, Any]:
    return {"choices": [{"index": 0, "message": {"role": "assistant", "content": content}}]}


def stub_reply(httpserver: HTTPServer, content: str) -> None:
    httpserver.expect_request(CHAT_PATH, method="POST").respond_with_json(chat_body(content))


@pytest.fixture
def slow_handler() -> Iterator[Callable[[Request], Response]]:
    """A stub handler that stays silent until the test releases it (the stub serves one request at a time)."""
    release = threading.Event()

    def handler(request: Request) -> Response:
        release.wait(SLOW_REPLY_MAX_S)
        return Response(json.dumps(chat_body("late")), content_type="application/json")

    yield handler
    release.set()


@pytest.fixture
def dropping_server_url() -> Iterator[str]:
    """A TCP server that accepts a connection and closes it at once, so the HTTP client sees a network error."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()

    def serve() -> None:
        while True:
            try:
                connection, _ = listener.accept()
            except OSError:
                return
            connection.close()

    threading.Thread(target=serve, daemon=True).start()
    yield f"http://127.0.0.1:{listener.getsockname()[1]}/v1"
    listener.close()


@pytest.fixture
def stub_base_url(httpserver: HTTPServer) -> str:
    return httpserver.url_for("/openai/v1")


@pytest.fixture
async def groq_client(stub_base_url: str) -> AsyncIterator[GroqClient]:
    async with httpx.AsyncClient() as http:
        yield GroqClient(http, base_url=stub_base_url, model=MODEL, timeout=TIMEOUT_S)


@pytest.fixture
def settings(stub_base_url: str) -> Settings:
    return SettingsFactory.build(
        groq_base_url=stub_base_url,
        model=MODEL,
        timeout_s=TIMEOUT_S,
        max_input_chars=MAX_CHARS,
        reasoning_effort="low",
    )
