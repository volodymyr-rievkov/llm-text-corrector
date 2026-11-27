from pathlib import Path

import pydantic
import pytest

from llm_text_corrector.frontend.config import FrontendSettings, get_frontend_settings


@pytest.mark.usefixtures("clean_env")
def test_defaults() -> None:
    settings = FrontendSettings()

    assert settings.backend_url is None  # None = talk to the backend in the same process
    assert settings.request_timeout_s == 35


def test_env_overrides_defaults(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("CORRECTOR_BACKEND_URL", "http://backend.test:9000")
    clean_env.setenv("CORRECTOR_REQUEST_TIMEOUT_S", "4.5")

    settings = FrontendSettings()

    assert settings.backend_url == "http://backend.test:9000"
    assert settings.request_timeout_s == 4.5


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CORRECTOR_BACKEND_URL", ""),
        ("CORRECTOR_BACKEND_URL", "not a url"),
        ("CORRECTOR_BACKEND_URL", "ftp://backend.test"),
        ("CORRECTOR_REQUEST_TIMEOUT_S", "0"),
        ("CORRECTOR_REQUEST_TIMEOUT_S", "-1"),
        ("CORRECTOR_REQUEST_TIMEOUT_S", "soon"),
    ],
)
def test_invalid_values_are_rejected(clean_env: pytest.MonkeyPatch, name: str, value: str) -> None:
    clean_env.setenv(name, value)

    with pytest.raises(pydantic.ValidationError):
        FrontendSettings()


def test_unprefixed_variables_are_ignored(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("BACKEND_URL", "http://wrong.test")

    assert FrontendSettings().backend_url is None


def test_reads_dotenv_file_by_default(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("CORRECTOR_BACKEND_URL=http://from-file.test\n", encoding="utf-8")

    assert FrontendSettings().backend_url == "http://from-file.test"


@pytest.mark.usefixtures("clean_env")
def test_get_frontend_settings_is_cached() -> None:
    get_frontend_settings.cache_clear()

    assert get_frontend_settings() is get_frontend_settings()
    get_frontend_settings.cache_clear()
