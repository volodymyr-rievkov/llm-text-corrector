"""Tags that fence the user text in the prompt and the model answer in its reply."""

INPUT_OPEN = "<text>"
INPUT_CLOSE = "</text>"
OUTPUT_OPEN = "<corrected>"
OUTPUT_CLOSE = "</corrected>"

ALL_TAGS = (INPUT_OPEN, INPUT_CLOSE, OUTPUT_OPEN, OUTPUT_CLOSE)


def strip_tags(text: str) -> str:
    """Remove every delimiter tag, repeating until none is left (so `<te<text>xt>` cannot rebuild one)."""
    previous = None
    while text != previous:
        previous = text
        for tag in ALL_TAGS:
            text = text.replace(tag, "")
    return text
