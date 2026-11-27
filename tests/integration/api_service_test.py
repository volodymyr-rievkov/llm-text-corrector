"""Real FastAPI app, service and Groq adapter, with a local stub server standing in for Groq."""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

from llm_text_corrector.backend.api.app import create_api
from llm_text_corrector.backend.config import Settings, get_settings
from tests.integration.conftest import API_KEY, CHAT_PATH, MODEL, TIMEOUT_S, chat_body
from tests.shared.factories.config import SettingsFactory

URL = "/api/v1/corrections"
KEY_HEADER = {"X-Groq-Api-Key": API_KEY}
MAX_CHARS = 40


@pytest.fixture
def settings(stub_base_url: str) -> Settings:
    return SettingsFactory.build(
        groq_base_url=stub_base_url,
        model=MODEL,
        timeout_s=TIMEOUT_S,
        max_input_chars=MAX_CHARS,
        reasoning_effort="low",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_api()
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:  # `with` runs the lifespan that owns the httpx client
        yield test_client


def stub_reply(httpserver: HTTPServer, content: str) -> None:
    httpserver.expect_request(CHAT_PATH, method="POST").respond_with_json(chat_body(content))


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("<corrected>I have an apple.</corrected>", "I have an apple."),
        (
            "Sure, here is the corrected text:\n<corrected>I have an apple.</corrected>\nHope this helps!",
            "I have an apple.",
        ),
        ("Ось виправлений текст:\n<corrected>У мене є яблуко.</corrected>\nГарного дня!", "У мене є яблуко."),
        ("<corrected>\n```\nI have an apple.\n```\n</corrected>", "I have an apple."),
        ('<corrected>"I have an apple."</corrected>', "I have an apple."),
    ],
)
def test_reply_with_extras_yields_only_the_corrected_text(
    client: TestClient, httpserver: HTTPServer, reply: str, expected: str
) -> None:
    stub_reply(httpserver, reply)

    response = client.post(URL, json={"text": "i has a apple"}, headers=KEY_HEADER)

    assert response.status_code == 200
    assert response.json() == {"corrected_text": expected}


def test_stub_receives_the_users_key_and_text(client: TestClient, httpserver: HTTPServer, settings: Settings) -> None:
    stub_reply(httpserver, "<corrected>ok</corrected>")

    client.post(URL, json={"text": "i has a apple"}, headers=KEY_HEADER)

    received, _ = httpserver.log[0]
    body = received.get_json()
    assert received.headers["Authorization"] == f"Bearer {API_KEY}"
    assert body["model"] == settings.model
    assert body["temperature"] == 0
    assert body["reasoning_effort"] == settings.reasoning_effort
    assert body["messages"][-1]["content"] == "<text>i has a apple</text>"


@pytest.mark.parametrize(
    ("stub_status", "status", "code"),
    [
        (401, 401, "invalid_api_key"),
        (403, 401, "invalid_api_key"),
        (429, 429, "rate_limited"),
        (500, 502, "provider_error"),
        (503, 502, "provider_error"),
    ],
)
def test_groq_error_status_maps_to_api_error(
    client: TestClient, httpserver: HTTPServer, stub_status: int, status: int, code: str
) -> None:
    httpserver.expect_request(CHAT_PATH, method="POST").respond_with_json({"error": API_KEY}, status=stub_status)

    response = client.post(URL, json={"text": "i has a apple"}, headers=KEY_HEADER)

    assert response.status_code == status
    assert response.json()["code"] == code
    assert API_KEY not in response.text


def test_slow_groq_reply_maps_to_gateway_timeout(
    client: TestClient, httpserver: HTTPServer, slow_handler: Callable[[Request], Response]
) -> None:
    httpserver.expect_request(CHAT_PATH, method="POST").respond_with_handler(slow_handler)

    response = client.post(URL, json={"text": "i has a apple"}, headers=KEY_HEADER)

    assert response.status_code == 504
    assert response.json()["code"] == "provider_timeout"


@pytest.mark.parametrize("reply", ["No tags, just chatter.", "<corrected>cut off", "<corrected>  </corrected>"])
def test_reply_without_usable_tags_maps_to_provider_error(
    client: TestClient, httpserver: HTTPServer, reply: str
) -> None:
    stub_reply(httpserver, reply)

    response = client.post(URL, json={"text": "i has a apple"}, headers=KEY_HEADER)

    assert response.status_code == 502
    assert response.json()["code"] == "provider_error"


@pytest.mark.parametrize(
    ("payload", "headers", "status", "code"),
    [
        ({"text": "   "}, KEY_HEADER, 422, "empty_input"),
        ({"text": "x" * (MAX_CHARS + 1)}, KEY_HEADER, 422, "input_too_long"),
        ({"text": "fine"}, {}, 401, "missing_api_key"),
        ({"text": "fine"}, {"X-Groq-Api-Key": "  "}, 401, "missing_api_key"),
        ({"nope": 1}, KEY_HEADER, 422, "invalid_request"),
    ],
)
def test_rejected_requests_never_reach_groq(
    client: TestClient,
    httpserver: HTTPServer,
    payload: dict[str, object],
    headers: dict[str, str],
    status: int,
    code: str,
) -> None:
    response = client.post(URL, json=payload, headers=headers)

    assert response.status_code == status
    assert response.json()["code"] == code
    assert httpserver.log == []


def test_health_works_without_key_or_groq(client: TestClient, httpserver: HTTPServer) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert httpserver.log == []


def test_non_ascii_key_is_rejected_before_any_call(client: TestClient, httpserver: HTTPServer) -> None:
    response = client.post(URL, json={"text": "i has a apple"}, headers={b"X-Groq-Api-Key": "kéy".encode("latin-1")})

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_api_key"
    assert httpserver.log == []
