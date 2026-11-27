"""The correction use case: validate, ask the LLM once, sanitize the reply."""

from llm_text_corrector.backend.domain.errors import (
    EmptyInputError,
    InputTooLongError,
    InvalidApiKeyError,
    MissingApiKeyError,
    ProviderError,
)
from llm_text_corrector.backend.domain.models import CorrectionRequest, CorrectionResult
from llm_text_corrector.backend.llm.client import LLMClient
from llm_text_corrector.backend.prompts import build_messages
from llm_text_corrector.backend.sanitizer import clean_output


class CorrectionService:
    def __init__(self, llm: LLMClient, *, max_input_chars: int) -> None:
        self._llm = llm
        self._max_input_chars = max_input_chars

    async def correct(self, request: CorrectionRequest, *, api_key: str) -> CorrectionResult:
        self._validate(request, api_key)
        reply = await self._llm.complete(build_messages(request.text), api_key=api_key)
        corrected = clean_output(reply, request.text)
        if not corrected:
            raise ProviderError
        return CorrectionResult(corrected_text=corrected)

    def _validate(self, request: CorrectionRequest, api_key: str) -> None:
        if not api_key.strip():
            raise MissingApiKeyError
        if not api_key.isascii():
            raise InvalidApiKeyError
        if not request.text.strip():
            raise EmptyInputError
        if len(request.text) > self._max_input_chars:
            raise InputTooLongError
