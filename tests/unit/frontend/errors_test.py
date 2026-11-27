import pytest

from llm_text_corrector.frontend.errors import CorrectionFailedError, FrontendError, InvalidInputError


@pytest.mark.parametrize("error_class", [FrontendError, InvalidInputError, CorrectionFailedError])
def test_error_carries_a_user_facing_message(error_class: type[FrontendError]) -> None:
    error = error_class("Check your Groq API key.")

    assert error.message == "Check your Groq API key."
    assert str(error) == "Check your Groq API key."


@pytest.mark.parametrize("error_class", [InvalidInputError, CorrectionFailedError])
def test_specific_errors_are_frontend_errors(error_class: type[FrontendError]) -> None:
    assert issubclass(error_class, FrontendError)
