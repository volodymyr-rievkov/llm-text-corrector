import pytest

from llm_text_corrector.backend.delimiters import ALL_TAGS, strip_tags


@pytest.mark.parametrize("tag", ALL_TAGS)
def test_removes_every_tag(tag: str) -> None:
    assert strip_tags(f"a{tag}b") == "ab"


@pytest.mark.parametrize("text", ["<te<text>xt>", "<</text>/text>", "<corr<corrected>ected>", "<<text>text>"])
def test_nested_tags_cannot_rebuild_a_tag(text: str) -> None:
    result = strip_tags(text)

    assert not any(tag in result for tag in ALL_TAGS)


def test_text_without_tags_is_unchanged() -> None:
    text = 'Plain "text" with <b>html</b>.\nSecond line.'

    assert strip_tags(text) == text
