import pydantic
import pytest

from llm_text_corrector.backend.api.schemas import CorrectionBody, CorrectionResponse, ErrorResponse, HealthResponse


def test_body_requires_text() -> None:
    with pytest.raises(pydantic.ValidationError):
        CorrectionBody.model_validate({})


def test_response_shapes() -> None:
    assert CorrectionResponse(corrected_text="x").model_dump() == {"corrected_text": "x"}
    assert ErrorResponse(code="c", detail="d").model_dump() == {"code": "c", "detail": "d"}
    assert HealthResponse().model_dump() == {"status": "ok"}
