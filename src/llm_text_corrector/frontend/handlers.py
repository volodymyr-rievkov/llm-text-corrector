"""UI-agnostic use case: validate the form, then ask the backend. Raises `FrontendError`s."""

from llm_text_corrector.frontend import texts
from llm_text_corrector.frontend.client import BackendClient
from llm_text_corrector.frontend.errors import InvalidInputError


def _is_header_safe(key: str) -> bool:
    """A key must be visible ASCII without spaces, or it cannot travel in an HTTP header."""
    return key.isascii() and key.isprintable() and " " not in key


async def correct_text(text: str, api_key: str, client: BackendClient) -> str:
    key = api_key.strip()  # pasted keys often carry a trailing space or newline
    if not key:
        raise InvalidInputError(texts.MSG_ENTER_KEY)
    if not text.strip():
        raise InvalidInputError(texts.MSG_EMPTY_INPUT)
    if not _is_header_safe(key):
        raise InvalidInputError(texts.MSG_CHECK_KEY)
    return await client.correct(text, key)
