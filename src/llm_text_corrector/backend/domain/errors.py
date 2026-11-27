"""Domain errors: a stable machine `code` and a safe, generic `detail` (never the key or user text)."""


class CorrectorError(Exception):
    code = "corrector_error"
    default_detail = "The text could not be corrected."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class EmptyInputError(CorrectorError):
    code = "empty_input"
    default_detail = "The text is empty."


class InputTooLongError(CorrectorError):
    code = "input_too_long"
    default_detail = "The text is longer than the allowed limit."


class MissingApiKeyError(CorrectorError):
    code = "missing_api_key"
    default_detail = "The API key is missing."


class InvalidApiKeyError(CorrectorError):
    code = "invalid_api_key"
    default_detail = "The provider rejected the API key."


class RateLimitedError(CorrectorError):
    code = "rate_limited"
    default_detail = "The provider rate limit was reached. Try again later."


class ProviderError(CorrectorError):
    code = "provider_error"
    default_detail = "The provider failed to return a usable answer."


class ProviderTimeoutError(CorrectorError):
    code = "provider_timeout"
    default_detail = "The provider did not answer in time."
