"""Turns a raw model reply into the bare corrected text; no output tags means an empty result."""

import re

from llm_text_corrector.backend.delimiters import OUTPUT_CLOSE, OUTPUT_OPEN, strip_tags

_FENCE = re.compile(r"\A```(?:[^\n`]*\n)?(.*?)\n?```\Z", re.DOTALL)
_QUOTE_PAIRS = (('"', '"'), ("'", "'"), ("“", "”"), ("„", "“"), ("‘", "’"), ("«", "»"))


def _extract_tagged(raw: str) -> str:
    """Return what sits between the first open and the last close output tag, or "" if either is missing."""
    start = raw.find(OUTPUT_OPEN)
    end = raw.rfind(OUTPUT_CLOSE)
    if start == -1 or end < start + len(OUTPUT_OPEN):
        return ""
    return raw[start + len(OUTPUT_OPEN) : end]


def _strip_fence(text: str) -> str:
    match = _FENCE.match(text)
    return match.group(1) if match else text


def _strip_wrapping_quotes(text: str) -> str:
    for opening, closing in _QUOTE_PAIRS:
        inner = text[1:-1]
        if (
            len(text) >= 2
            and text[0] == opening
            and text[-1] == closing
            and opening not in inner
            and closing not in inner
        ):
            return inner
    return text


def clean_output(raw: str, original: str) -> str:
    """Extract the answer from `raw`; strip a wrapper only if the user's `original` text had none."""
    text = strip_tags(_extract_tagged(raw)).strip()
    source = original.strip()
    if _strip_fence(source) == source:
        text = _strip_fence(text).strip()
    if _strip_wrapping_quotes(source) == source:
        text = _strip_wrapping_quotes(text).strip()
    return text
