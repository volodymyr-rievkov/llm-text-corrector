from unittest.mock import AsyncMock

import httpx
import pytest
from pytest_mock import MockerFixture

from llm_text_corrector.frontend import texts
from llm_text_corrector.frontend.client import BackendClient
from llm_text_corrector.frontend.errors import CorrectionFailedError
from tests.shared.factories.api import CorrectionResponseFactory, ErrorResponseFactory

BASE_URL = "http://backend.test"
TIMEOUT_S = 12.5
API_KEY = "gsk_frontend_secret"
TEXT = "I has a apple."


@pytest.fixture
def http() -> httpx.AsyncClient:
    return httpx.AsyncClient()


@pytest.fixture
def post(mocker: MockerFixture, http: httpx.AsyncClient) -> AsyncMock:
    return mocker.patch.object(http, "post", new_callable=mocker.AsyncMock)


@pytest.fixture
def client(http: httpx.AsyncClient) -> BackendClient:
    return BackendClient(BASE_URL + "/", TIMEOUT_S, http)


def reply(post: AsyncMock, response: httpx.Response | Exception) -> None:
    if isinstance(response, Exception):
        post.side_effect = response
    else:
        post.return_value = response


async def test_sends_text_and_key_to_the_corrections_endpoint(client: BackendClient, post: AsyncMock) -> None:
    reply(post, httpx.Response(200, json=CorrectionResponseFactory.build().model_dump()))

    await client.correct(TEXT, API_KEY)

    post.assert_awaited_once_with(
        f"{BASE_URL}/api/v1/corrections",
        headers={"X-Groq-Api-Key": API_KEY},
        json={"text": TEXT},
        timeout=TIMEOUT_S,
    )


async def test_returns_the_corrected_text(client: BackendClient, post: AsyncMock) -> None:
    body = CorrectionResponseFactory.build()
    reply(post, httpx.Response(200, json=body.model_dump()))

    assert await client.correct(TEXT, API_KEY) == body.corrected_text


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("missing_api_key", texts.MSG_CHECK_KEY),
        ("invalid_api_key", texts.MSG_CHECK_KEY),
        ("empty_input", texts.MSG_EMPTY_INPUT),
        ("input_too_long", texts.MSG_TOO_LONG),
        ("rate_limited", texts.MSG_RATE_LIMITED),
        ("provider_error", texts.MSG_PROVIDER_ERROR),
        ("provider_timeout", texts.MSG_PROVIDER_TIMEOUT),
        ("internal_error", texts.MSG_GENERIC),
        ("some_new_code", texts.MSG_GENERIC),
    ],
)
async def test_backend_error_code_becomes_a_user_message(
    client: BackendClient, post: AsyncMock, code: str, message: str
) -> None:
    reply(post, httpx.Response(422, json=ErrorResponseFactory.build(code=code).model_dump()))

    with pytest.raises(CorrectionFailedError) as caught:
        await client.correct(TEXT, API_KEY)

    assert caught.value.message == message


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(502, text="<html>Bad gateway</html>"),
        httpx.Response(500, json=["not", "an", "object"]),
        httpx.Response(500, json={"detail": "no code field"}),
        httpx.Response(500, json={"code": 42, "detail": "code is not a string"}),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"unexpected": "shape"}),
        httpx.Response(200, json={"corrected_text": 7}),
    ],
    ids=["html", "json-list", "no-code", "code-not-string", "ok-not-json", "ok-wrong-shape", "ok-text-not-string"],
)
async def test_unusable_response_gives_the_generic_message(
    client: BackendClient, post: AsyncMock, response: httpx.Response
) -> None:
    reply(post, response)

    with pytest.raises(CorrectionFailedError) as caught:
        await client.correct(TEXT, API_KEY)

    assert caught.value.message == texts.MSG_GENERIC


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("refused"),
        httpx.ReadTimeout("slow"),
        httpx.InvalidURL("bad"),
        UnicodeEncodeError("ascii", "а", 0, 1, "ordinal not in range(128)"),
    ],
    ids=["connect", "timeout", "invalid-url", "unencodable-header"],
)
async def test_network_failure_gives_the_generic_message(
    client: BackendClient, post: AsyncMock, error: Exception
) -> None:
    reply(post, error)

    with pytest.raises(CorrectionFailedError) as caught:
        await client.correct(TEXT, API_KEY)

    assert caught.value.message == texts.MSG_GENERIC


async def test_the_key_never_reaches_the_error_message(client: BackendClient, post: AsyncMock) -> None:
    leaky = ErrorResponseFactory.build(code="invalid_api_key", detail=f"bad key {API_KEY}")
    reply(post, httpx.Response(401, json=leaky.model_dump()))

    with pytest.raises(CorrectionFailedError) as caught:
        await client.correct(TEXT, API_KEY)

    assert API_KEY not in caught.value.message
    assert API_KEY not in str(caught.value)
    assert caught.value.__cause__ is None


async def test_the_key_never_reaches_the_error_of_a_network_failure(client: BackendClient, post: AsyncMock) -> None:
    reply(post, httpx.ConnectError(f"cannot reach {API_KEY}"))

    with pytest.raises(CorrectionFailedError) as caught:
        await client.correct(TEXT, API_KEY)

    assert API_KEY not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
