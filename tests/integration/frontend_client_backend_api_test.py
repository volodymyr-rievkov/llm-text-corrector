"""Real frontend client talking to the real backend app in-process, with a stub server standing in for Groq."""

from collections.abc import AsyncIterator

import httpx
import pytest
from pytest_httpserver import HTTPServer

from llm_text_corrector.backend.api.app import create_api
from llm_text_corrector.backend.config import Settings, get_settings
from llm_text_corrector.frontend import texts
from llm_text_corrector.frontend.client import BackendClient
from llm_text_corrector.frontend.errors import CorrectionFailedError
from tests.integration.conftest import API_KEY, CHAT_PATH, MAX_CHARS, stub_reply

BASE_URL = "http://backend.test"
REQUEST_TIMEOUT_S = 5
TEXT = "i has a apple"


@pytest.fixture
async def backend_client(settings: Settings) -> AsyncIterator[BackendClient]:
    app = create_api()
    app.dependency_overrides[get_settings] = lambda: settings
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=httpx.ASGITransport(app=app)) as http:
        yield BackendClient(BASE_URL, REQUEST_TIMEOUT_S, http)


async def test_returns_the_corrected_text(backend_client: BackendClient, httpserver: HTTPServer) -> None:
    stub_reply(httpserver, "<corrected>I have an apple.</corrected>")

    assert await backend_client.correct(TEXT, API_KEY) == "I have an apple."


async def test_chatty_reply_is_cleaned_to_the_corrected_text_only(
    backend_client: BackendClient, httpserver: HTTPServer
) -> None:
    stub_reply(httpserver, "Sure, here it is:\n<corrected>У мене є яблуко.</corrected>\nHope this helps!")

    assert await backend_client.correct(TEXT, API_KEY) == "У мене є яблуко."


async def test_groq_receives_the_key_the_user_typed(backend_client: BackendClient, httpserver: HTTPServer) -> None:
    stub_reply(httpserver, "<corrected>ok</corrected>")

    await backend_client.correct(TEXT, API_KEY)

    (request, _) = httpserver.log[0]
    assert request.headers["Authorization"] == f"Bearer {API_KEY}"


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, texts.MSG_CHECK_KEY),
        (429, texts.MSG_RATE_LIMITED),
        (500, texts.MSG_PROVIDER_ERROR),
    ],
)
async def test_groq_failure_reaches_the_user_as_a_friendly_message(
    backend_client: BackendClient, httpserver: HTTPServer, status: int, message: str
) -> None:
    httpserver.expect_request(CHAT_PATH, method="POST").respond_with_data("nope", status=status)

    with pytest.raises(CorrectionFailedError) as caught:
        await backend_client.correct(TEXT, API_KEY)

    assert caught.value.message == message


@pytest.mark.parametrize(
    ("text", "key", "message"),
    [
        ("   ", API_KEY, texts.MSG_EMPTY_INPUT),
        ("x" * (MAX_CHARS + 1), API_KEY, texts.MSG_TOO_LONG),
        (TEXT, "", texts.MSG_CHECK_KEY),
    ],
)
async def test_backend_rejection_never_reaches_groq(
    backend_client: BackendClient, httpserver: HTTPServer, text: str, key: str, message: str
) -> None:
    with pytest.raises(CorrectionFailedError) as caught:
        await backend_client.correct(text, key)

    assert caught.value.message == message
    assert httpserver.log == []


async def test_unreachable_backend_gives_the_generic_message() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(refuse)) as http:
        with pytest.raises(CorrectionFailedError) as caught:
            await BackendClient(BASE_URL, REQUEST_TIMEOUT_S, http).correct(TEXT, API_KEY)

    assert caught.value.message == texts.MSG_GENERIC
