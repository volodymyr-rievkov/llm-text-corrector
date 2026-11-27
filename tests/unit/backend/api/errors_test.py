import json
import logging

import pytest
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request

from llm_text_corrector.backend.api.errors import (
    corrector_error_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from llm_text_corrector.backend.domain import errors

REQUEST = Request({"type": "http"})
SECRET = "secret-user-text"

# Mirrors the error table in specs/backend/SPEC.md.
EXPECTED = [
    (errors.EmptyInputError, 422),
    (errors.InputTooLongError, 422),
    (errors.MissingApiKeyError, 401),
    (errors.InvalidApiKeyError, 401),
    (errors.RateLimitedError, 429),
    (errors.ProviderError, 502),
    (errors.ProviderTimeoutError, 504),
]


@pytest.mark.parametrize(("error_cls", "status"), EXPECTED)
async def test_maps_domain_error_to_status_code_and_detail(error_cls: type[errors.CorrectorError], status: int) -> None:
    error = error_cls()

    response = await corrector_error_handler(REQUEST, error)

    assert response.status_code == status
    assert json.loads(bytes(response.body)) == {"code": error.code, "detail": error.detail}


async def test_unmapped_domain_error_is_a_500() -> None:
    error = errors.CorrectorError()

    response = await corrector_error_handler(REQUEST, error)

    assert response.status_code == 500
    assert json.loads(bytes(response.body))["code"] == error.code


async def test_validation_error_is_invalid_request_without_echoing_input() -> None:
    exc = RequestValidationError([{"type": "string_type", "loc": ("body", "text"), "msg": "bad", "input": SECRET}])

    response = await validation_error_handler(REQUEST, exc)

    body = json.loads(bytes(response.body))
    assert response.status_code == 422
    assert body["code"] == "invalid_request"
    assert SECRET not in json.dumps(body)


async def test_subclass_of_a_mapped_error_inherits_its_status() -> None:
    class CustomRateLimitError(errors.RateLimitedError):
        code = "custom_rate_limit"

    response = await corrector_error_handler(REQUEST, CustomRateLimitError())

    assert response.status_code == 429
    assert json.loads(bytes(response.body))["code"] == "custom_rate_limit"


async def test_unexpected_error_is_a_generic_500_without_leaking_its_message(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        response = await unexpected_error_handler(REQUEST, RuntimeError(SECRET))

    body = json.loads(bytes(response.body))
    assert response.status_code == 500
    assert body["code"] == "internal_error"
    assert SECRET not in json.dumps(body)
    assert SECRET not in caplog.text
    assert "RuntimeError" in caplog.text


@pytest.mark.parametrize(
    ("status", "code"),
    [(404, "not_found"), (405, "method_not_allowed"), (418, "http_error"), (500, "http_error")],
)
async def test_http_error_uses_the_error_body_and_keeps_its_status(status: int, code: str) -> None:
    response = await http_error_handler(REQUEST, HTTPException(status_code=status, detail=SECRET))

    body = json.loads(bytes(response.body))
    assert response.status_code == status
    assert body["code"] == code
    assert body["detail"]
    assert SECRET not in json.dumps(body)


async def test_http_error_keeps_its_headers() -> None:
    exc = HTTPException(status_code=405, headers={"Allow": "POST"})

    response = await http_error_handler(REQUEST, exc)

    assert response.headers["allow"] == "POST"
