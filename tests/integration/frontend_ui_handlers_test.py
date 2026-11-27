"""The page callback with the real form handler and backend client (in-memory HTTP stub behind them)."""

from collections.abc import AsyncIterator, Callable

import gradio as gr
import httpx
import pytest

from llm_text_corrector.frontend import texts
from llm_text_corrector.frontend.client import BackendClient
from llm_text_corrector.frontend.ui import build_ui, correct_for_ui
from tests.shared.factories.api import CorrectionResponseFactory, ErrorResponseFactory

API_KEY = "gsk_ui_integration_secret"
TEXT = "i has a apple"
CORRECTED = "I have an apple."

type ClientMaker = Callable[[httpx.Response], BackendClient]


@pytest.fixture
async def make_client() -> AsyncIterator[ClientMaker]:
    """Builds a client whose backend always answers with the given response, and closes them afterwards."""
    opened: list[httpx.AsyncClient] = []

    def make(response: httpx.Response) -> BackendClient:
        http = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response))
        opened.append(http)
        return BackendClient("http://backend.test", 5, http)

    yield make
    for http in opened:
        await http.aclose()


@pytest.fixture
def ok_client(make_client: ClientMaker) -> BackendClient:
    body = CorrectionResponseFactory.build(corrected_text=CORRECTED).model_dump()
    return make_client(httpx.Response(200, json=body))


async def test_page_callback_returns_the_corrected_text(ok_client: BackendClient) -> None:
    (callback,) = [fn.fn for fn in build_ui(ok_client).fns.values() if fn.api_name == "correct"]

    assert callback is not None
    assert await callback(TEXT, API_KEY) == CORRECTED


async def test_backend_error_becomes_a_gradio_alert(make_client: ClientMaker) -> None:
    body = ErrorResponseFactory.build(code="invalid_api_key").model_dump()

    with pytest.raises(gr.Error) as caught:
        await correct_for_ui(TEXT, API_KEY, make_client(httpx.Response(401, json=body)))

    assert caught.value.message == texts.MSG_CHECK_KEY


async def test_blank_key_becomes_a_gradio_alert(ok_client: BackendClient) -> None:
    with pytest.raises(gr.Error) as caught:
        await correct_for_ui(TEXT, "", ok_client)

    assert caught.value.message == texts.MSG_ENTER_KEY
