from polyfactory.factories import DataclassFactory

from llm_text_corrector.backend.domain.models import CorrectionRequest, CorrectionResult


class CorrectionRequestFactory(DataclassFactory[CorrectionRequest]):
    __model__ = CorrectionRequest


class CorrectionResultFactory(DataclassFactory[CorrectionResult]):
    __model__ = CorrectionResult
