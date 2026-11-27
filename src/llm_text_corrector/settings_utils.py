"""Validators shared by the backend and frontend settings."""

from pydantic import AnyHttpUrl, TypeAdapter

_HTTP_URL = TypeAdapter(AnyHttpUrl)


def require_http_url(value: str) -> str:
    """Fail at startup on a malformed URL; the string is kept as written."""
    _HTTP_URL.validate_python(value)
    return value
