import dataclasses
from typing import Any

import pytest
from polyfactory.factories import DataclassFactory

from tests.shared.factories.domain import CorrectionRequestFactory, CorrectionResultFactory


def test_request_keeps_text() -> None:
    request = CorrectionRequestFactory.build()

    assert request.text


def test_result_keeps_corrected_text() -> None:
    result = CorrectionResultFactory.build()

    assert result.corrected_text


@pytest.mark.parametrize("factory", [CorrectionRequestFactory, CorrectionResultFactory])
def test_models_are_immutable(factory: type[DataclassFactory[Any]]) -> None:
    model = factory.build()
    field = dataclasses.fields(model)[0].name

    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(model, field, "changed")
