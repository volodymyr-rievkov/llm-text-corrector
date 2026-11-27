"""Real `GroqClient` over real HTTP against a local stub server."""

from collections.abc import Callable

import httpx
import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

from llm_text_corrector.backend.domain import errors
from llm_text_corrector.backend.llm.groq import GroqClient
from llm_text_corrector.backend.prompts import build_messages
from tests.integration.conftest import API_KEY, CHAT_PATH, MODEL, TIMEOUT_S, chat_body
from tests.shared.factories.domain import CorrectionRequestFactory

REPLY = "<corrected>Fixed.</corrected>"


async def test_sends_a_correct_request_and_returns_the_reply(groq_client: GroqClient, httpserver: HTTPServer) -> None:
    httpserver.expect_request(CHAT_PATH, method="POST").respond_with_json(chat_body(REPLY))
    messages = build_messages(CorrectionRequestFactory.build().text)

    reply = await groq_client.complete(messages, api_key=API_KEY)

    assert reply == REPLY
    received, _ = httpserver.log[0]
    assert received.headers["Authorization"] == f"Bearer {API_KEY}"
    assert received.get_json() == {"model": MODEL, "messages": messages, "temperature": 0}


@pytest.mark.parametrize(
    ("status", "error_cls"),
    [
        (401, errors.InvalidApiKeyError),
        (403, errors.InvalidApiKeyError),
        (429, errors.RateLimitedError),
        (500, errors.ProviderError),
        (503, errors.ProviderError),
    ],
)
async def test_http_error_status_becomes_domain_error(
    groq_client: GroqClient, httpserver: HTTPServer, status: int, error_cls: type[errors.CorrectorError]
) -> None:
    httpserver.expect_request(CHAT_PATH, method="POST").respond_with_json({"error": {"message": "nope"}}, status=status)

    with pytest.raises(error_cls):
        await groq_client.complete(build_messages("text"), api_key=API_KEY)


async def test_reply_slower_than_the_timeout_becomes_provider_timeout(
    groq_client: GroqClient, httpserver: HTTPServer, slow_handler: Callable[[Request], Response]
) -> None:
    httpserver.expect_request(CHAT_PATH, method="POST").respond_with_handler(slow_handler)

    with pytest.raises(errors.ProviderTimeoutError):
        await groq_client.complete(build_messages("text"), api_key=API_KEY)


@pytest.mark.parametrize("body", ["not json at all", "{}", '{"choices": []}', '{"choices": [{"message": {}}]}'])
async def test_unusable_body_becomes_provider_error(groq_client: GroqClient, httpserver: HTTPServer, body: str) -> None:
    httpserver.expect_request(CHAT_PATH, method="POST").respond_with_data(body, content_type="application/json")

    with pytest.raises(errors.ProviderError):
        await groq_client.complete(build_messages("text"), api_key=API_KEY)


async def test_unknown_route_becomes_provider_error(groq_client: GroqClient) -> None:
    # No handler registered: the stub answers 500 to anything.
    with pytest.raises(errors.ProviderError):
        await groq_client.complete(build_messages("text"), api_key=API_KEY)


async def test_dropped_connection_becomes_provider_error(dropping_server_url: str) -> None:
    async with httpx.AsyncClient() as http:
        client = GroqClient(http, base_url=dropping_server_url, model=MODEL, timeout=TIMEOUT_S)

        with pytest.raises(errors.ProviderError):
            await client.complete(build_messages("text"), api_key=API_KEY)


async def test_reasoning_effort_reaches_the_stub_as_json(stub_base_url: str, httpserver: HTTPServer) -> None:
    httpserver.expect_request(CHAT_PATH, method="POST").respond_with_json(chat_body(REPLY))
    async with httpx.AsyncClient() as http:
        client = GroqClient(http, base_url=stub_base_url, model=MODEL, timeout=TIMEOUT_S, reasoning_effort="low")

        await client.complete(build_messages("text"), api_key=API_KEY)

    received, _ = httpserver.log[0]
    assert received.get_json()["reasoning_effort"] == "low"
