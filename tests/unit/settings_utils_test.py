import pydantic
import pytest

from llm_text_corrector.settings_utils import require_http_url

URL = "http://example.test:8080/path/"


@pytest.mark.parametrize("url", [URL, "https://example.test", "http://127.0.0.1:7860"])
def test_valid_http_urls_are_kept_as_written(url: str) -> None:
    assert require_http_url(url) == url


@pytest.mark.parametrize("url", ["", "not a url", "ftp://example.test", "example.test"])
def test_anything_else_is_rejected(url: str) -> None:
    with pytest.raises(pydantic.ValidationError):
        require_http_url(url)
