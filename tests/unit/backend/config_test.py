from pathlib import Path

import pydantic
import pytest

from llm_text_corrector.backend.config import Settings, get_settings


def write_dotenv(directory: Path, *lines: str) -> None:
    (directory / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.usefixtures("clean_env")
def test_defaults() -> None:
    settings = Settings()

    assert settings.groq_base_url == "https://api.groq.com/openai/v1"
    assert settings.model == "openai/gpt-oss-120b"
    assert settings.timeout_s == 30
    assert settings.max_input_chars == 5000
    assert settings.reasoning_effort == "low"


def test_env_overrides_defaults(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("CORRECTOR_GROQ_BASE_URL", "http://localhost:9999/v1")
    clean_env.setenv("CORRECTOR_MODEL", "other-model")
    clean_env.setenv("CORRECTOR_TIMEOUT_S", "2.5")
    clean_env.setenv("CORRECTOR_MAX_INPUT_CHARS", "100")
    clean_env.setenv("CORRECTOR_REASONING_EFFORT", "high")

    settings = Settings()

    assert settings.groq_base_url == "http://localhost:9999/v1"
    assert settings.model == "other-model"
    assert settings.timeout_s == 2.5
    assert settings.max_input_chars == 100
    assert settings.reasoning_effort == "high"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CORRECTOR_TIMEOUT_S", "0"),
        ("CORRECTOR_TIMEOUT_S", "-1"),
        ("CORRECTOR_TIMEOUT_S", "soon"),
        ("CORRECTOR_MAX_INPUT_CHARS", "0"),
        ("CORRECTOR_MAX_INPUT_CHARS", "many"),
        ("CORRECTOR_MODEL", ""),
        ("CORRECTOR_GROQ_BASE_URL", ""),
        ("CORRECTOR_GROQ_BASE_URL", "not a url"),
        ("CORRECTOR_GROQ_BASE_URL", "ftp://groq.test/v1"),
        ("CORRECTOR_REASONING_EFFORT", "extreme"),
        ("CORRECTOR_REASONING_EFFORT", "minimal"),
        ("CORRECTOR_REASONING_EFFORT", ""),
    ],
)
def test_invalid_values_are_rejected(clean_env: pytest.MonkeyPatch, name: str, value: str) -> None:
    clean_env.setenv(name, value)

    with pytest.raises(pydantic.ValidationError):
        Settings()


def test_unprefixed_variables_are_ignored(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("MODEL", "wrong")
    clean_env.setenv("TIMEOUT_S", "1")

    settings = Settings()

    assert settings.model == "openai/gpt-oss-120b"
    assert settings.timeout_s == 30


def test_reads_dotenv_file_by_default(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    write_dotenv(tmp_path, "CORRECTOR_MODEL=from-file", "CORRECTOR_MAX_INPUT_CHARS=77")

    settings = Settings()

    assert settings.model == "from-file"
    assert settings.max_input_chars == 77


def test_real_environment_beats_dotenv_file(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    write_dotenv(tmp_path, "CORRECTOR_MODEL=from-file")
    clean_env.setenv("CORRECTOR_MODEL", "from-env")

    assert Settings().model == "from-env"


def test_unrelated_dotenv_entries_are_ignored(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    write_dotenv(tmp_path, "SOMETHING_ELSE=1", "CORRECTOR_TIMEOUT_S=3")

    assert Settings().timeout_s == 3


def test_missing_dotenv_file_is_fine(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assert Settings().model == "openai/gpt-oss-120b"


@pytest.mark.usefixtures("clean_env")
def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()

    assert get_settings() is get_settings()
    get_settings.cache_clear()


@pytest.mark.parametrize("value", ["none", "None"])
def test_reasoning_effort_can_be_switched_off(clean_env: pytest.MonkeyPatch, value: str) -> None:
    clean_env.setenv("CORRECTOR_REASONING_EFFORT", value)

    assert Settings().reasoning_effort is None


@pytest.mark.parametrize("value", ["low", "medium", "high"])
def test_reasoning_effort_accepts_the_levels_the_model_supports(clean_env: pytest.MonkeyPatch, value: str) -> None:
    clean_env.setenv("CORRECTOR_REASONING_EFFORT", value)

    assert Settings().reasoning_effort == value
