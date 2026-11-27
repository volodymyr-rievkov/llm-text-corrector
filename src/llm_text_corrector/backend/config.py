"""Runtime settings from CORRECTOR_* environment variables, falling back to a local .env file."""

from functools import lru_cache
from typing import Annotated

from pydantic import AfterValidator, AnyHttpUrl, Field, TypeAdapter, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from llm_text_corrector.backend.domain.models import ReasoningEffort

_HTTP_URL = TypeAdapter(AnyHttpUrl)


def _require_http_url(value: str) -> str:
    """Fail at startup on a malformed URL; the string is kept as written."""
    _HTTP_URL.validate_python(value)
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CORRECTOR_", env_file=".env", extra="ignore", frozen=True)

    groq_base_url: Annotated[str, AfterValidator(_require_http_url)] = Field(
        default="https://api.groq.com/openai/v1", min_length=1
    )
    model: str = Field(default="openai/gpt-oss-120b", min_length=1)
    timeout_s: float = Field(default=30, gt=0)
    max_input_chars: int = Field(default=5000, gt=0)
    reasoning_effort: ReasoningEffort | None = "low"

    @field_validator("reasoning_effort", mode="before")
    @classmethod
    def _none_means_off(cls, value: object) -> object:
        """`none` (any case) switches the setting off, for models that reject the parameter."""
        return None if isinstance(value, str) and value.lower() == "none" else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
