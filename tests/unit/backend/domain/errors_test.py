import pytest

from llm_text_corrector.backend.domain import errors

ERROR_CODES = [
    (errors.EmptyInputError, "empty_input"),
    (errors.InputTooLongError, "input_too_long"),
    (errors.MissingApiKeyError, "missing_api_key"),
    (errors.InvalidApiKeyError, "invalid_api_key"),
    (errors.RateLimitedError, "rate_limited"),
    (errors.ProviderError, "provider_error"),
    (errors.ProviderTimeoutError, "provider_timeout"),
]


@pytest.mark.parametrize(("error_cls", "code"), ERROR_CODES)
def test_error_has_stable_code(error_cls: type[errors.CorrectorError], code: str) -> None:
    assert error_cls.code == code


@pytest.mark.parametrize("error_cls", [cls for cls, _ in ERROR_CODES])
def test_error_has_safe_default_message(error_cls: type[errors.CorrectorError]) -> None:
    error = error_cls()

    assert str(error)
    assert error.detail == str(error)


@pytest.mark.parametrize("error_cls", [cls for cls, _ in ERROR_CODES])
def test_error_is_a_corrector_error(error_cls: type[errors.CorrectorError]) -> None:
    assert issubclass(error_cls, errors.CorrectorError)


def test_error_messages_are_unique() -> None:
    messages = {error_cls().detail for error_cls, _ in ERROR_CODES}

    assert len(messages) == len(ERROR_CODES)


def test_error_accepts_custom_detail() -> None:
    error = errors.ProviderError("custom")

    assert error.detail == "custom"
