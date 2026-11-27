"""The port the service depends on, so the provider can change without touching it."""

from typing import Protocol

from llm_text_corrector.backend.domain.models import Message


class LLMClient(Protocol):
    async def complete(self, messages: list[Message], *, api_key: str) -> str:
        """Return the raw model reply; raise a `CorrectorError` subclass on any failure."""
        ...
