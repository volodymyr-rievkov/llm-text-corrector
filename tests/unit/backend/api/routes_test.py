import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from llm_text_corrector.backend.domain import errors
from llm_text_corrector.backend.domain.models import CorrectionRequest, CorrectionResult
from llm_text_corrector.backend.service import CorrectionService
from tests.shared.factories.domain import CorrectionRequestFactory
from tests.unit.backend.api.conftest import API_KEY

URL = "/api/v1/corrections"
KEY_HEADER = {"X-Groq-Api-Key": API_KEY}
SECRET_TEXT = "secret-user-text"

# Mirrors the error table in specs/backend/SPEC.md.
ERROR_TABLE = [
    (errors.EmptyInputError, 422, "empty_input"),
    (errors.InputTooLongError, 422, "input_too_long"),
    (errors.MissingApiKeyError, 401, "missing_api_key"),
    (errors.InvalidApiKeyError, 401, "invalid_api_key"),
    (errors.RateLimitedError, 429, "rate_limited"),
    (errors.ProviderError, 502, "provider_error"),
    (errors.ProviderTimeoutError, 504, "provider_timeout"),
]


def test_returns_corrected_text(client: TestClient, result: CorrectionResult) -> None:
    request = CorrectionRequestFactory.build()

    response = client.post(URL, json={"text": request.text}, headers=KEY_HEADER)

    assert response.status_code == 200
    assert response.json() == {"corrected_text": result.corrected_text}


def test_passes_text_and_header_key_to_service(client: TestClient, service: CorrectionService) -> None:
    request = CorrectionRequestFactory.build()

    client.post(URL, json={"text": request.text}, headers=KEY_HEADER)

    service.correct.assert_awaited_once_with(  # type: ignore[attr-defined]
        CorrectionRequest(text=request.text), api_key=API_KEY
    )


def test_missing_key_header_is_passed_as_blank(client: TestClient, service: CorrectionService) -> None:
    request = CorrectionRequestFactory.build()

    client.post(URL, json={"text": request.text})

    service.correct.assert_awaited_once_with(CorrectionRequest(text=request.text), api_key="")  # type: ignore[attr-defined]


@pytest.mark.parametrize(("error_cls", "status", "code"), ERROR_TABLE)
def test_domain_errors_become_error_responses(
    client: TestClient, service: CorrectionService, error_cls: type[errors.CorrectorError], status: int, code: str
) -> None:
    service.correct.side_effect = error_cls()  # type: ignore[attr-defined]
    request = CorrectionRequestFactory.build()

    response = client.post(URL, json={"text": request.text}, headers=KEY_HEADER)

    assert response.status_code == status
    assert response.json() == {"code": code, "detail": error_cls.default_detail}


@pytest.mark.parametrize(
    "raw_body",
    [
        b"{}",
        b'{"text": 5}',
        b'{"text": ["secret-user-text"]}',
        b'["secret-user-text"]',
        b"{not json",
    ],
)
def test_malformed_body_is_invalid_request(client: TestClient, service: CorrectionService, raw_body: bytes) -> None:
    headers = {**KEY_HEADER, "Content-Type": "application/json"}

    response = client.post(URL, content=raw_body, headers=headers)

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
    assert SECRET_TEXT not in response.text
    service.correct.assert_not_awaited()  # type: ignore[attr-defined]


@pytest.mark.parametrize(("error_cls", "_status", "_code"), ERROR_TABLE)
def test_key_is_never_echoed_on_errors(
    client: TestClient, service: CorrectionService, error_cls: type[errors.CorrectorError], _status: int, _code: str
) -> None:
    service.correct.side_effect = error_cls()  # type: ignore[attr-defined]

    failure = client.post(URL, json={"text": "x"}, headers=KEY_HEADER)
    invalid = client.post(URL, json={}, headers=KEY_HEADER)

    for response in (failure, invalid):
        assert API_KEY not in response.text
        assert API_KEY not in str(response.headers)


def test_key_is_not_echoed_on_success(client: TestClient) -> None:
    response = client.post(URL, json={"text": "x"}, headers=KEY_HEADER)

    assert API_KEY not in response.text
    assert API_KEY not in str(response.headers)


def test_health_needs_no_key_and_no_llm_call(client: TestClient, service: CorrectionService) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    service.correct.assert_not_awaited()  # type: ignore[attr-defined]


def test_unexpected_failure_still_returns_the_error_body(api: FastAPI, service: CorrectionService) -> None:
    service.correct.side_effect = RuntimeError(SECRET_TEXT)  # type: ignore[attr-defined]
    request = CorrectionRequestFactory.build()

    response = TestClient(api, raise_server_exceptions=False).post(URL, json={"text": request.text}, headers=KEY_HEADER)

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert SECRET_TEXT not in response.text


def test_unknown_route_returns_the_error_body(client: TestClient) -> None:
    response = client.get("/nope")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert set(response.json()) == {"code", "detail"}


def test_wrong_method_returns_the_error_body_and_allow_header(client: TestClient) -> None:
    response = client.get(URL)

    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"
    assert response.headers["allow"] == "POST"
