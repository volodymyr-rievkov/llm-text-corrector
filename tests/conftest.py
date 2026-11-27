"""Marks each test as unit or integration based on its directory."""

from pathlib import Path

import pytest

_MARKS_BY_DIR = {"unit": pytest.mark.unit, "integration": pytest.mark.integration}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        for part in Path(item.fspath).parts:
            if part in _MARKS_BY_DIR:
                item.add_marker(_MARKS_BY_DIR[part])
