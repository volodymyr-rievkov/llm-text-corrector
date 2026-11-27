"""The combined app: the real API and the real Gradio page behind one ASGI app."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from llm_text_corrector.frontend import texts
from llm_text_corrector.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:  # `with` runs the lifespans
        yield test_client


def test_api_health_is_not_shadowed_by_the_page(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_the_page_with_its_title(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert f'"title":"{texts.PAGE_TITLE}"' in response.text  # Gradio 6 sets the tab title from this config


def test_corrections_endpoint_is_reachable_through_the_combined_app(client: TestClient) -> None:
    response = client.post("/api/v1/corrections", json={"text": "hi"})

    assert response.status_code == 401
    assert response.json()["code"] == "missing_api_key"
