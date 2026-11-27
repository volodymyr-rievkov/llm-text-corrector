import logging
from typing import Any

import httpx
import pytest
from pytest_mock import MockerFixture

from llm_text_corrector.backend.domain import errors
from llm_text_corrector.backend.llm.client import LLMClient
from llm_text_corrector.backend.llm.groq import GroqClient
from llm_text_corrector.backend.prompts import build_messages
from tests.shared.factories.domain import CorrectionRequestFactory

BASE_URL = "https://groq.example/openai/v1"
MODEL = "test-model"
API_KEY = "gsk_super_secret_key"
REPLY = "<corrected>Fixed.</corrected>"


def make_response(status: int = 200, *, json: Any = None, content: bytes | None = None) -> httpx.Response:
    request = httpx.Request("POST", f"{BASE_URL}/chat/completions")
    if content is not None:
        return httpx.Response(status, content=content, request=request)
    return httpx.Response(status, json=json, request=request)


def ok_body(content: Any = REPLY) -> dict[str, Any]:
    return {"choices": [{"index": 0, "message": {"role": "assistant", "content": content}}]}


@pytest.fixture
def http(mocker: MockerFixture) -> httpx.AsyncClient:
    client = httpx.AsyncClient()
    mocker.patch.object(client, "post", return_value=make_response(json=ok_body()))
    return client


@pytest.fixture
def groq(http: httpx.AsyncClient) -> GroqClient:
    return GroqClient(http, base_url=BASE_URL + "/", model=MODEL, timeout=12.5)


async def test_sends_expected_request(groq: GroqClient, http: httpx.AsyncClient) -> None:
    messages = build_messages(CorrectionRequestFactory.build().text)

    await groq.complete(messages, api_key=API_KEY)

    http.post.assert_awaited_once_with(  # type: ignore[attr-defined]
        f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": MODEL, "messages": messages, "temperature": 0},
        timeout=12.5,
    )


def test_satisfies_the_llm_port(groq: GroqClient) -> None:
    port: LLMClient = groq  # mypy checks the Protocol

    assert port is groq


async def test_returns_reply_content(groq: GroqClient) -> None:
    messages = build_messages(CorrectionRequestFactory.build().text)

    assert await groq.complete(messages, api_key=API_KEY) == REPLY


@pytest.mark.parametrize(
    ("status", "error_cls"),
    [
        (401, errors.InvalidApiKeyError),
        (403, errors.InvalidApiKeyError),
        (429, errors.RateLimitedError),
        (400, errors.ProviderError),
        (404, errors.ProviderError),
        (500, errors.ProviderError),
        (503, errors.ProviderError),
    ],
)
async def test_translates_error_status(
    groq: GroqClient, http: httpx.AsyncClient, mocker: MockerFixture, status: int, error_cls: type[Exception]
) -> None:
    mocker.patch.object(http, "post", return_value=make_response(status, json={"error": {"message": API_KEY}}))

    with pytest.raises(error_cls):
        await groq.complete(build_messages("text"), api_key=API_KEY)


@pytest.mark.parametrize(
    "response",
    [
        make_response(content=b"not json"),
        make_response(json=[]),
        make_response(json={}),
        make_response(json={"choices": []}),
        make_response(json={"choices": [{}]}),
        make_response(json={"choices": [{"message": {}}]}),
        make_response(json={"choices": [{"message": {"content": None}}]}),
        make_response(json={"choices": [{"message": {"content": 5}}]}),
        make_response(json={"choices": ["oops"]}),
    ],
)
async def test_malformed_reply_is_provider_error(
    groq: GroqClient, http: httpx.AsyncClient, mocker: MockerFixture, response: httpx.Response
) -> None:
    mocker.patch.object(http, "post", return_value=response)

    with pytest.raises(errors.ProviderError):
        await groq.complete(build_messages("text"), api_key=API_KEY)


@pytest.mark.parametrize(
    ("raised", "error_cls"),
    [
        (httpx.ReadTimeout("slow"), errors.ProviderTimeoutError),
        (httpx.ConnectTimeout("slow"), errors.ProviderTimeoutError),
        (httpx.ConnectError("down"), errors.ProviderError),
        (httpx.RemoteProtocolError("bad"), errors.ProviderError),
    ],
)
async def test_translates_transport_errors(
    groq: GroqClient, http: httpx.AsyncClient, mocker: MockerFixture, raised: Exception, error_cls: type[Exception]
) -> None:
    mocker.patch.object(http, "post", side_effect=raised)

    with pytest.raises(error_cls):
        await groq.complete(build_messages("text"), api_key=API_KEY)


@pytest.mark.parametrize(
    "failure",
    [
        {"return_value": make_response(401, json={"error": API_KEY})},
        {"return_value": make_response(500, content=API_KEY.encode())},
        {"return_value": make_response(json={"choices": [{"message": {"content": None}}]})},
        {"side_effect": httpx.ConnectError(API_KEY)},
        {"side_effect": httpx.ReadTimeout(API_KEY)},
    ],
)
async def test_key_never_appears_in_errors(
    groq: GroqClient, http: httpx.AsyncClient, mocker: MockerFixture, failure: dict[str, Any]
) -> None:
    mocker.patch.object(http, "post", **failure)

    with pytest.raises(errors.CorrectorError) as raised:
        await groq.complete(build_messages("text"), api_key=API_KEY)

    assert API_KEY not in str(raised.value)
    assert API_KEY not in raised.value.detail
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__


async def test_invalid_url_is_provider_error(groq: GroqClient, http: httpx.AsyncClient, mocker: MockerFixture) -> None:
    mocker.patch.object(http, "post", side_effect=httpx.InvalidURL("bad"))

    with pytest.raises(errors.ProviderError):
        await groq.complete(build_messages("text"), api_key=API_KEY)


@pytest.mark.parametrize(
    "failure",
    [
        {"return_value": make_response(500, content=API_KEY.encode())},
        {"side_effect": httpx.ConnectError(API_KEY)},
        {"side_effect": httpx.ReadTimeout(API_KEY)},
    ],
)
async def test_failures_are_logged_without_the_key(
    groq: GroqClient,
    http: httpx.AsyncClient,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
    failure: dict[str, Any],
) -> None:
    mocker.patch.object(http, "post", **failure)

    with caplog.at_level(logging.WARNING), pytest.raises(errors.CorrectorError):
        await groq.complete(build_messages("text"), api_key=API_KEY)

    assert caplog.records
    assert API_KEY not in caplog.text


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
async def test_sends_reasoning_effort_when_configured(http: httpx.AsyncClient, effort: str) -> None:
    groq = GroqClient(http, base_url=BASE_URL, model=MODEL, timeout=12.5, reasoning_effort=effort)  # type: ignore[arg-type]

    await groq.complete(build_messages("text"), api_key=API_KEY)

    sent = http.post.await_args.kwargs["json"]  # type: ignore[attr-defined]
    assert sent["reasoning_effort"] == effort


async def test_omits_reasoning_effort_when_not_configured(groq: GroqClient, http: httpx.AsyncClient) -> None:
    await groq.complete(build_messages("text"), api_key=API_KEY)

    assert "reasoning_effort" not in http.post.await_args.kwargs["json"]  # type: ignore[attr-defined]
