"""Maps domain errors and request-validation failures to the `{code, detail}` error body."""

import logging
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from llm_text_corrector.backend.api.schemas import ErrorResponse
from llm_text_corrector.backend.domain import errors

_STATUS_BY_ERROR: dict[type[errors.CorrectorError], int] = {
    errors.EmptyInputError: 422,
    errors.InputTooLongError: 422,
    errors.MissingApiKeyError: 401,
    errors.InvalidApiKeyError: 401,
    errors.RateLimitedError: 429,
    errors.ProviderError: 502,
    errors.ProviderTimeoutError: 504,
}
_DEFAULT_STATUS = 500
_INVALID_REQUEST_CODE = "invalid_request"
_INVALID_REQUEST_DETAIL = "The request body is malformed."
_HTTP_ERRORS = {
    404: ("not_found", "The resource was not found."),
    405: ("method_not_allowed", "The method is not allowed for this resource."),
}
_HTTP_ERROR_FALLBACK = ("http_error", "The request could not be processed.")
_INTERNAL_ERROR_CODE = "internal_error"
_INTERNAL_ERROR_DETAIL = "Something went wrong on the server."

logger = logging.getLogger(__name__)


def _error_response(status: int, code: str, detail: str, headers: dict[str, str] | None = None) -> JSONResponse:
    content = ErrorResponse(code=code, detail=detail).model_dump()
    return JSONResponse(status_code=status, content=content, headers=headers)


def _status_for(error: errors.CorrectorError) -> int:
    """Status of the closest mapped class, so a new subclass inherits its parent's status."""
    for cls in type(error).__mro__:
        if cls in _STATUS_BY_ERROR:
            return _STATUS_BY_ERROR[cls]
    return _DEFAULT_STATUS


async def corrector_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(errors.CorrectorError, exc)
    return _error_response(_status_for(error), error.code, error.detail)


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Routing failures (404, 405, ...) keep their status and headers (e.g. `Allow`) in the error body shape."""
    http_exc = cast(HTTPException, exc)
    code, detail = _HTTP_ERRORS.get(http_exc.status_code, _HTTP_ERROR_FALLBACK)
    return _error_response(http_exc.status_code, code, detail, dict(http_exc.headers or {}))


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the class only: the message may contain the key or the user's text.
    logger.error("Unhandled %s", type(exc).__name__)
    return _error_response(_DEFAULT_STATUS, _INTERNAL_ERROR_CODE, _INTERNAL_ERROR_DETAIL)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never echo `exc.errors()`: it contains the submitted input.
    return _error_response(422, _INVALID_REQUEST_CODE, _INVALID_REQUEST_DETAIL)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(errors.CorrectorError, corrector_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
