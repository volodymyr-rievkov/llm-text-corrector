"""Groq chat-completions adapter (OpenAI-compatible API) that maps failures to domain errors."""

import logging
from typing import Any

import httpx

from llm_text_corrector.backend.domain.errors import (
    InvalidApiKeyError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitedError,
)
from llm_text_corrector.backend.domain.models import Message, ReasoningEffort

logger = logging.getLogger(__name__)

_AUTH_STATUSES = {401, 403}
_RATE_LIMIT_STATUS = 429


class GroqClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        base_url: str,
        model: str,
        timeout: float,
        reasoning_effort: ReasoningEffort | None = None,
    ) -> None:
        self._http = http
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._timeout = timeout
        self._reasoning_effort = reasoning_effort

    async def complete(self, messages: list[Message], *, api_key: str) -> str:
        try:
            response = await self._http.post(
                self._url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=self._payload(messages),
                timeout=self._timeout,
            )
        except httpx.TimeoutException:
            logger.warning("Groq call timed out")
            raise ProviderTimeoutError from None
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            logger.warning("Groq call failed: %s", type(exc).__name__)
            raise ProviderError from None
        _raise_for_status(response.status_code)
        return _parse_content(response)

    def _payload(self, messages: list[Message]) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": self._model, "messages": messages, "temperature": 0}
        if self._reasoning_effort is not None:
            payload["reasoning_effort"] = self._reasoning_effort
        return payload


def _raise_for_status(status: int) -> None:
    if status in _AUTH_STATUSES:
        raise InvalidApiKeyError from None
    if status == _RATE_LIMIT_STATUS:
        raise RateLimitedError from None
    if status >= 400:
        logger.warning("Groq answered with status %s", status)
        raise ProviderError from None


def _parse_content(response: httpx.Response) -> str:
    try:
        body: Any = response.json()
        content = body["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise ProviderError from None
    if not isinstance(content, str):
        raise ProviderError from None
    return content
