"""UI settings from CORRECTOR_* environment variables, falling back to a local .env file."""

from functools import lru_cache
from typing import Annotated

from pydantic import AfterValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from llm_text_corrector.settings_utils import require_http_url


class FrontendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CORRECTOR_", env_file=".env", extra="ignore", frozen=True)

    # None means the API runs in the same process and is called directly, whatever port the server uses.
    backend_url: Annotated[str, AfterValidator(require_http_url)] | None = None
    request_timeout_s: float = Field(default=35, gt=0)


@lru_cache
def get_frontend_settings() -> FrontendSettings:
    return FrontendSettings()
