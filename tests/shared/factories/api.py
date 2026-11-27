from polyfactory.factories.pydantic_factory import ModelFactory

from llm_text_corrector.backend.api.schemas import CorrectionResponse, ErrorResponse


class CorrectionResponseFactory(ModelFactory[CorrectionResponse]):
    __model__ = CorrectionResponse


class ErrorResponseFactory(ModelFactory[ErrorResponse]):
    __model__ = ErrorResponse
