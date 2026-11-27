import pytest
from pytest_mock import MockerFixture

from llm_text_corrector.backend.domain import errors
from llm_text_corrector.backend.domain.models import CorrectionResult
from llm_text_corrector.backend.llm.client import LLMClient
from llm_text_corrector.backend.prompts import build_messages
from llm_text_corrector.backend.service import CorrectionService
from tests.shared.factories.domain import CorrectionRequestFactory

MAX_CHARS = 50
API_KEY = "gsk_key"


@pytest.fixture
def llm(mocker: MockerFixture) -> LLMClient:
    client = mocker.create_autospec(LLMClient, instance=True)
    client.complete.return_value = "<corrected>Fixed text.</corrected>"
    return client


@pytest.fixture
def service(llm: LLMClient) -> CorrectionService:
    return CorrectionService(llm, max_input_chars=MAX_CHARS)


async def test_returns_sanitized_corrected_text(service: CorrectionService, llm: LLMClient) -> None:
    request = CorrectionRequestFactory.build(text="Some text")
    llm.complete.return_value = "Sure! <corrected>Fixed text.</corrected> Bye."  # type: ignore[attr-defined]

    result = await service.correct(request, api_key=API_KEY)

    assert result == CorrectionResult(corrected_text="Fixed text.")


async def test_sends_built_prompt_and_key_to_llm(service: CorrectionService, llm: LLMClient) -> None:
    request = CorrectionRequestFactory.build(text="Some text")

    await service.correct(request, api_key=API_KEY)

    llm.complete.assert_awaited_once_with(build_messages(request.text), api_key=API_KEY)  # type: ignore[attr-defined]


async def test_accepts_text_of_exactly_the_limit(service: CorrectionService) -> None:
    request = CorrectionRequestFactory.build(text="a" * MAX_CHARS)

    result = await service.correct(request, api_key=API_KEY)

    assert result.corrected_text == "Fixed text."


@pytest.mark.parametrize("api_key", ["", "   ", "\t\n"])
async def test_blank_key_is_rejected_without_calling_llm(
    service: CorrectionService, llm: LLMClient, api_key: str
) -> None:
    request = CorrectionRequestFactory.build(text="Some text")

    with pytest.raises(errors.MissingApiKeyError):
        await service.correct(request, api_key=api_key)

    llm.complete.assert_not_awaited()  # type: ignore[attr-defined]


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
async def test_blank_text_is_rejected_without_calling_llm(
    service: CorrectionService, llm: LLMClient, text: str
) -> None:
    request = CorrectionRequestFactory.build(text=text)

    with pytest.raises(errors.EmptyInputError):
        await service.correct(request, api_key=API_KEY)

    llm.complete.assert_not_awaited()  # type: ignore[attr-defined]


async def test_too_long_text_is_rejected_without_calling_llm(service: CorrectionService, llm: LLMClient) -> None:
    request = CorrectionRequestFactory.build(text="a" * (MAX_CHARS + 1))

    with pytest.raises(errors.InputTooLongError):
        await service.correct(request, api_key=API_KEY)

    llm.complete.assert_not_awaited()  # type: ignore[attr-defined]


@pytest.mark.parametrize("reply", ["", "No tags at all", "<corrected>   </corrected>", "<corrected>cut off"])
async def test_unusable_reply_is_provider_error(service: CorrectionService, llm: LLMClient, reply: str) -> None:
    request = CorrectionRequestFactory.build(text="Some text")
    llm.complete.return_value = reply  # type: ignore[attr-defined]

    with pytest.raises(errors.ProviderError):
        await service.correct(request, api_key=API_KEY)


@pytest.mark.parametrize(
    "error",
    [errors.InvalidApiKeyError(), errors.RateLimitedError(), errors.ProviderError(), errors.ProviderTimeoutError()],
)
async def test_llm_errors_pass_through(
    service: CorrectionService, llm: LLMClient, error: errors.CorrectorError
) -> None:
    request = CorrectionRequestFactory.build(text="Some text")
    llm.complete.side_effect = error  # type: ignore[attr-defined]

    with pytest.raises(type(error)) as raised:
        await service.correct(request, api_key=API_KEY)

    assert raised.value is error


@pytest.mark.parametrize("api_key", ["gsk_kéy", "ключ"])
async def test_non_ascii_key_is_rejected_without_calling_llm(
    service: CorrectionService, llm: LLMClient, api_key: str
) -> None:
    request = CorrectionRequestFactory.build(text="Some text")

    with pytest.raises(errors.InvalidApiKeyError):
        await service.correct(request, api_key=api_key)

    llm.complete.assert_not_awaited()  # type: ignore[attr-defined]


async def test_wrapper_written_by_the_user_is_kept(service: CorrectionService, llm: LLMClient) -> None:
    request = CorrectionRequestFactory.build(text='"to be or not to be."')
    llm.complete.return_value = '<corrected>"To be or not to be."</corrected>'  # type: ignore[attr-defined]

    result = await service.correct(request, api_key=API_KEY)

    assert result.corrected_text == '"To be or not to be."'
