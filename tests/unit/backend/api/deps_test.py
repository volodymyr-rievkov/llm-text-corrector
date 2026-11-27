import httpx
import pytest
from fastapi import FastAPI
from pytest_mock import MockerFixture
from starlette.requests import Request

from llm_text_corrector.backend.api.deps import get_api_key, get_http_client, get_llm_client, get_service
from llm_text_corrector.backend.domain.errors import InputTooLongError
from llm_text_corrector.backend.prompts import build_messages
from tests.shared.factories.config import SettingsFactory
from tests.shared.factories.domain import CorrectionRequestFactory

REPLY = {"choices": [{"message": {"content": "<corrected>ok</corrected>"}}]}


def test_http_client_comes_from_app_state() -> None:
    app = FastAPI()
    app.state.http_client = httpx.AsyncClient()

    assert get_http_client(Request({"type": "http", "app": app})) is app.state.http_client


async def test_llm_client_uses_settings(mocker: MockerFixture) -> None:
    settings = SettingsFactory.build(groq_base_url="http://groq.test/v1", model="m-1", timeout_s=7)
    http = httpx.AsyncClient()
    response = httpx.Response(200, json=REPLY, request=httpx.Request("POST", "http://groq.test"))
    post = mocker.patch.object(http, "post", return_value=response)
    messages = build_messages(CorrectionRequestFactory.build().text)

    await get_llm_client(settings, http).complete(messages, api_key="k")

    assert post.await_args is not None
    assert post.await_args.args == ("http://groq.test/v1/chat/completions",)
    assert post.await_args.kwargs["json"]["model"] == "m-1"
    assert post.await_args.kwargs["timeout"] == 7


async def test_service_uses_max_input_chars_from_settings(mocker: MockerFixture) -> None:
    settings = SettingsFactory.build(max_input_chars=3)
    llm = mocker.AsyncMock()
    request = CorrectionRequestFactory.build(text="abcd")

    with pytest.raises(InputTooLongError):
        await get_service(settings, llm).correct(request, api_key="k")


@pytest.mark.parametrize(("header", "expected"), [("abc", "abc"), ("  abc " + "\n", "abc"), ("   ", ""), (None, "")])
def test_api_key_comes_from_header(header: str | None, expected: str) -> None:
    assert get_api_key(header) == expected


@pytest.mark.parametrize("effort", ["low", "high", None])
async def test_llm_client_passes_reasoning_effort_from_settings(mocker: MockerFixture, effort: str | None) -> None:
    settings = SettingsFactory.build(reasoning_effort=effort)
    http = httpx.AsyncClient()
    response = httpx.Response(200, json=REPLY, request=httpx.Request("POST", "http://groq.test"))
    post = mocker.patch.object(http, "post", return_value=response)

    await get_llm_client(settings, http).complete(build_messages("text"), api_key="k")

    assert post.await_args is not None
    assert post.await_args.kwargs["json"].get("reasoning_effort") == effort
