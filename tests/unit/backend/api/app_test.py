from fastapi.testclient import TestClient

from llm_text_corrector.backend.api.app import create_api


def test_each_call_builds_a_fresh_app() -> None:
    assert create_api() is not create_api()


def test_lifespan_owns_a_shared_http_client() -> None:
    app = create_api()

    with TestClient(app):
        http = app.state.http_client
        assert not http.is_closed

    assert http.is_closed
