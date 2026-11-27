import pytest
from pytest_mock import MockerFixture

from llm_text_corrector.frontend import texts
from llm_text_corrector.frontend.client import BackendClient
from llm_text_corrector.frontend.errors import CorrectionFailedError, InvalidInputError
from llm_text_corrector.frontend.handlers import correct_text

API_KEY = "gsk_handler_secret"
TEXT = "I has a apple."
CORRECTED = "I have an apple."


@pytest.fixture
def client(mocker: MockerFixture) -> BackendClient:
    mock = mocker.create_autospec(BackendClient, instance=True)
    mock.correct.return_value = CORRECTED
    return mock


async def test_returns_the_corrected_text(client: BackendClient) -> None:
    assert await correct_text(TEXT, API_KEY, client) == CORRECTED

    client.correct.assert_awaited_once_with(TEXT, API_KEY)  # type: ignore[attr-defined]


@pytest.mark.parametrize("key", ["", " ", "\t\n"])
async def test_blank_key_is_rejected_without_a_request(client: BackendClient, key: str) -> None:
    with pytest.raises(InvalidInputError) as caught:
        await correct_text(TEXT, key, client)

    assert caught.value.message == texts.MSG_ENTER_KEY
    client.correct.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.parametrize("text", ["", " ", "\n\t "])
async def test_blank_text_is_rejected_without_a_request(client: BackendClient, text: str) -> None:
    with pytest.raises(InvalidInputError) as caught:
        await correct_text(text, API_KEY, client)

    assert caught.value.message == texts.MSG_EMPTY_INPUT
    client.correct.assert_not_called()  # type: ignore[attr-defined]


async def test_blank_key_is_reported_before_blank_text(client: BackendClient) -> None:
    with pytest.raises(InvalidInputError) as caught:
        await correct_text("", "", client)

    assert caught.value.message == texts.MSG_ENTER_KEY


@pytest.mark.parametrize("padding", [" ", "\n", "\t ", "\r\n"])
async def test_surrounding_whitespace_is_trimmed_from_the_key(client: BackendClient, padding: str) -> None:
    await correct_text(TEXT, f"{padding}{API_KEY}{padding}", client)

    client.correct.assert_awaited_once_with(TEXT, API_KEY)  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "key",
    ["gsk_аbc", "ключ", "gsk abc", "gsk\tabc", "gsk\nabc", "gsk\x00abc", "gsk\x7fabc"],
    ids=["cyrillic-lookalike", "cyrillic", "inner-space", "inner-tab", "inner-newline", "nul", "del"],
)
async def test_malformed_key_is_rejected_without_a_request(client: BackendClient, key: str) -> None:
    with pytest.raises(InvalidInputError) as caught:
        await correct_text(TEXT, key, client)

    assert caught.value.message == texts.MSG_CHECK_KEY
    client.correct.assert_not_called()  # type: ignore[attr-defined]


async def test_blank_text_is_reported_before_a_malformed_key(client: BackendClient) -> None:
    with pytest.raises(InvalidInputError) as caught:
        await correct_text("", "ключ", client)

    assert caught.value.message == texts.MSG_EMPTY_INPUT


async def test_client_error_passes_through_with_its_message(client: BackendClient) -> None:
    client.correct.side_effect = CorrectionFailedError(texts.MSG_RATE_LIMITED)  # type: ignore[attr-defined]

    with pytest.raises(CorrectionFailedError) as caught:
        await correct_text(TEXT, API_KEY, client)

    assert caught.value.message == texts.MSG_RATE_LIMITED
