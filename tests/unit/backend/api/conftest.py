import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from llm_text_corrector.backend.api.app import create_api
from llm_text_corrector.backend.api.deps import get_service
from llm_text_corrector.backend.domain.models import CorrectionResult
from llm_text_corrector.backend.service import CorrectionService
from tests.shared.factories.domain import CorrectionResultFactory

API_KEY = "gsk_super_secret_key"


@pytest.fixture
def result() -> CorrectionResult:
    return CorrectionResultFactory.build()


@pytest.fixture
def service(mocker: MockerFixture, result: CorrectionResult) -> CorrectionService:
    mock = mocker.create_autospec(CorrectionService, instance=True)
    mock.correct.return_value = result
    return mock


@pytest.fixture
def api(service: CorrectionService) -> FastAPI:
    app = create_api()
    app.dependency_overrides[get_service] = lambda: service
    return app


@pytest.fixture
def client(api: FastAPI) -> TestClient:
    return TestClient(api)
