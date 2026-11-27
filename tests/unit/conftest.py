import os
from pathlib import Path

import pytest


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> pytest.MonkeyPatch:
    """Start from the defaults: no CORRECTOR_* variables and an empty working dir (so no .env)."""
    for name in [n for n in os.environ if n.startswith("CORRECTOR_")]:
        monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    return monkeypatch
