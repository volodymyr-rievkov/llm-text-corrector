"""The form handler with the real backend client; the backend itself is an in-memory HTTP stub."""

from collections.abc import AsyncIterator

import httpx
import pytest

from llm_text_corrector.frontend import texts
from llm_text_corrector.frontend.client import BackendClient
from llm_text_corrector.frontend.errors import CorrectionFailedError, InvalidInputError
from llm_text_corrector.frontend.handlers import correct_text
from tests.shared.factories.api import CorrectionResponseFactory, ErrorResponseFactory

API_KEY = "gsk_handler_integration_secret"
TEXT = "i has a apple"


@pytest.fixture
def received() -> list[httpx.Request]:
    return []


@pytest.fixture
async def client(received: list[httpx.Request]) -> AsyncIterator[BackendClient]:
    reply = httpx.Response(200, json=CorrectionResponseFactory.build(corrected_text="I have an apple.").model_dump())

    def handle(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return reply

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        yield BackendClient("http://backend.test", 5, http)


async def test_valid_form_reaches_the_backend_and_returns_its_text(
    client: BackendClient, received: list[httpx.Request]
) -> None:
    assert await correct_text(TEXT, API_KEY, client) == "I have an apple."

    (request,) = received
    assert request.headers["X-Groq-Api-Key"] == API_KEY


async def test_key_pasted_with_surrounding_whitespace_reaches_the_backend_trimmed(
    client: BackendClient, received: list[httpx.Request]
) -> None:
    await correct_text(TEXT, f"  {API_KEY}\n", client)

    (request,) = received
    assert request.headers["X-Groq-Api-Key"] == API_KEY


@pytest.mark.parametrize(("text", "key"), [("", API_KEY), (TEXT, "  "), (TEXT, "ключ"), (TEXT, "gsk abc")])
async def test_blank_field_sends_no_request(
    client: BackendClient, received: list[httpx.Request], text: str, key: str
) -> None:
    with pytest.raises(InvalidInputError):
        await correct_text(text, key, client)

    assert received == []


async def test_backend_error_surfaces_with_the_user_message() -> None:
    body = ErrorResponseFactory.build(code="rate_limited").model_dump()
    transport = httpx.MockTransport(lambda request: httpx.Response(429, json=body))

    async with httpx.AsyncClient(transport=transport) as http:
        with pytest.raises(CorrectionFailedError) as caught:
            await correct_text(TEXT, API_KEY, BackendClient("http://backend.test", 5, http))

    assert caught.value.message == texts.MSG_RATE_LIMITED
