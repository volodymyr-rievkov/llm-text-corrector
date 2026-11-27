"""HTTP client for the correction backend; turns every failure into a user-facing error."""

from typing import Any

import httpx

from llm_text_corrector.frontend import texts
from llm_text_corrector.frontend.errors import CorrectionFailedError

_CORRECTIONS_PATH = "/api/v1/corrections"
_KEY_HEADER = "X-Groq-Api-Key"


class BackendClient:
    def __init__(self, base_url: str, timeout: float, http: httpx.AsyncClient) -> None:
        self._url = f"{base_url.rstrip('/')}{_CORRECTIONS_PATH}"
        self._timeout = timeout
        self._http = http

    async def correct(self, text: str, api_key: str) -> str:
        try:
            response = await self._http.post(
                self._url, headers={_KEY_HEADER: api_key}, json={"text": text}, timeout=self._timeout
            )
        except (httpx.HTTPError, httpx.InvalidURL, UnicodeEncodeError):
            # `from None` drops the original error: its message may quote the key.
            raise CorrectionFailedError(texts.MSG_GENERIC) from None
        if not response.is_success:
            raise CorrectionFailedError(_message_for(response))
        return _read_text(response)


def _json_object(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _read_text(response: httpx.Response) -> str:
    text = _json_object(response).get("corrected_text")
    if not isinstance(text, str):
        raise CorrectionFailedError(texts.MSG_GENERIC)
    return text


def _message_for(response: httpx.Response) -> str:
    code = _json_object(response).get("code")
    return texts.ERROR_MESSAGES.get(code, texts.MSG_GENERIC) if isinstance(code, str) else texts.MSG_GENERIC
