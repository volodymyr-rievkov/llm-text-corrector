from unittest.mock import MagicMock

import gradio as gr
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from llm_text_corrector import main
from llm_text_corrector.backend.api.app import create_api
from llm_text_corrector.frontend.config import FrontendSettings
from tests.shared.factories.config import FrontendSettingsFactory


@pytest.fixture
def api(mocker: MockerFixture) -> FastAPI:
    built = create_api()
    mocker.patch.object(main, "create_api", return_value=built)
    return built


@pytest.fixture
def settings(mocker: MockerFixture) -> FrontendSettings:
    built = FrontendSettingsFactory.build()
    mocker.patch.object(main, "get_frontend_settings", return_value=built)
    return built


@pytest.fixture
def in_process_settings(mocker: MockerFixture) -> FrontendSettings:
    built = FrontendSettingsFactory.build(backend_url=None)
    mocker.patch.object(main, "get_frontend_settings", return_value=built)
    return built


@pytest.fixture
def build_ui(mocker: MockerFixture) -> MagicMock:
    return mocker.patch.object(main, "build_ui", return_value=gr.Blocks())


@pytest.fixture
def backend_client(mocker: MockerFixture) -> MagicMock:
    return mocker.patch.object(main, "BackendClient")


@pytest.fixture
def asgi_transport(mocker: MockerFixture) -> MagicMock:
    return mocker.patch.object(httpx, "ASGITransport", wraps=httpx.ASGITransport)


def http_client_of(backend_client: MagicMock) -> httpx.AsyncClient:
    http = backend_client.call_args.args[2]
    assert isinstance(http, httpx.AsyncClient)
    return http


@pytest.mark.usefixtures("settings", "build_ui")
def test_create_app_serves_the_api_and_mounts_the_ui_at_the_root(mocker: MockerFixture, api: FastAPI) -> None:
    mount = mocker.patch.object(gr, "mount_gradio_app", wraps=gr.mount_gradio_app)

    app = main.create_app()

    mount.assert_called_once_with(api, main.build_ui.return_value, path="/")  # type: ignore[attr-defined]
    assert {"/api/health", "/api/v1/corrections"} <= set(app.openapi()["paths"])


@pytest.mark.usefixtures("api")
def test_configured_backend_url_is_called_over_the_network(
    build_ui: MagicMock, backend_client: MagicMock, asgi_transport: MagicMock, settings: FrontendSettings
) -> None:
    main.create_app()

    backend_client.assert_called_once_with(
        settings.backend_url, settings.request_timeout_s, http_client_of(backend_client)
    )
    build_ui.assert_called_once_with(backend_client.return_value)
    asgi_transport.assert_not_called()


@pytest.mark.usefixtures("build_ui")
def test_without_a_backend_url_the_ui_talks_to_the_api_in_the_same_process(
    api: FastAPI, backend_client: MagicMock, asgi_transport: MagicMock, in_process_settings: FrontendSettings
) -> None:
    main.create_app()

    backend_client.assert_called_once_with(
        main.IN_PROCESS_BACKEND_URL, in_process_settings.request_timeout_s, http_client_of(backend_client)
    )
    asgi_transport.assert_called_once_with(app=api)


@pytest.mark.usefixtures("build_ui", "in_process_settings", "api")
async def test_in_process_client_reaches_the_api_without_a_network(backend_client: MagicMock) -> None:
    main.create_app()

    response = await http_client_of(backend_client).get(f"{main.IN_PROCESS_BACKEND_URL}/api/health")

    assert response.status_code == 200


@pytest.mark.usefixtures("build_ui", "settings", "api")
def test_the_http_client_stays_open_while_the_app_runs(backend_client: MagicMock) -> None:
    with TestClient(main.create_app()):  # `with` runs the lifespans
        assert not http_client_of(backend_client).is_closed


@pytest.mark.usefixtures("build_ui", "settings", "api")
def test_the_http_client_is_closed_when_the_app_shuts_down(backend_client: MagicMock) -> None:
    with TestClient(main.create_app()):
        pass

    assert http_client_of(backend_client).is_closed


def test_module_exposes_an_asgi_app() -> None:
    assert isinstance(main.app, FastAPI)
