from polyfactory.factories.pydantic_factory import ModelFactory

from llm_text_corrector.backend.config import Settings


class SettingsFactory(ModelFactory[Settings]):
    __model__ = Settings

    groq_base_url = "http://groq.test/v1"
