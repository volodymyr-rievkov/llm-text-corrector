from polyfactory.factories.pydantic_factory import ModelFactory

from llm_text_corrector.backend.config import Settings
from llm_text_corrector.frontend.config import FrontendSettings


class SettingsFactory(ModelFactory[Settings]):
    __model__ = Settings

    groq_base_url = "http://groq.test/v1"


class FrontendSettingsFactory(ModelFactory[FrontendSettings]):
    __model__ = FrontendSettings

    backend_url = "http://backend.test"
    request_timeout_s = 12.5
