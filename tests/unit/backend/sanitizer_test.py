import pytest

from llm_text_corrector.backend.delimiters import INPUT_CLOSE, INPUT_OPEN, OUTPUT_CLOSE, OUTPUT_OPEN
from llm_text_corrector.backend.sanitizer import clean_output

FIXED = "She goes to school."
ORIGINAL = "She go to scool."
FENCE = "```"


def tagged(body: str) -> str:
    return f"{OUTPUT_OPEN}{body}{OUTPUT_CLOSE}"


@pytest.mark.parametrize(
    ("intro", "outro"),
    [
        ("Sure, here is the corrected text:\n", "\nHope this helps!"),
        ("Ось виправлений текст:\n", "\nСподіваюся, це допоможе!"),
        ("Voici le texte corrigé :\n", ""),
        ("", "\n\nLet me know if you need more."),
        ("Hier ist der korrigierte Text: ", " Viel Erfolg!"),
    ],
)
def test_extracts_tagged_text_ignoring_surroundings(intro: str, outro: str) -> None:
    assert clean_output(f"{intro}{tagged(FIXED)}{outro}", ORIGINAL) == FIXED


def test_keeps_multiline_text() -> None:
    body = "Line one.\n\nLine two.\n  Indented."

    assert clean_output(tagged(body), ORIGINAL) == body


def test_trims_whitespace_inside_tags() -> None:
    assert clean_output(tagged(f"\n  {FIXED}  \n"), ORIGINAL) == FIXED


@pytest.mark.parametrize(
    "raw",
    [
        FIXED,
        f"Sure, here it is: {FIXED}",
        f"Intro {OUTPUT_OPEN}{FIXED}",
        f"{FIXED}{OUTPUT_CLOSE}",
        f"{OUTPUT_CLOSE}{FIXED}{OUTPUT_OPEN}",
        f"{INPUT_OPEN}{FIXED}{INPUT_CLOSE}",
        f"{FENCE}\n{FIXED}\n{FENCE}",
        f'"{FIXED}"',
    ],
)
def test_reply_without_both_output_tags_is_rejected(raw: str) -> None:
    assert clean_output(raw, ORIGINAL) == ""


@pytest.mark.parametrize(
    "body",
    [
        f"{INPUT_OPEN}{FIXED}{INPUT_CLOSE}",
        f"{FENCE}\n{FIXED}\n{FENCE}",
        f"{FENCE}text\n{FIXED}\n{FENCE}",
        f'"{FIXED}"',
        f"'{FIXED}'",
        f"“{FIXED}”",
        f"«{FIXED}»",
        f'{FENCE}\n"{FIXED}"\n{FENCE}',
    ],
)
def test_wrappers_inside_tags_are_removed(body: str) -> None:
    assert clean_output(tagged(body), ORIGINAL) == FIXED


@pytest.mark.parametrize(
    "text",
    [
        'He said "hi" and left.',
        '"Hi," he said, "bye."',
        "It's fine, isn't it?",
        "“One” and “two”",
        "Use `code` here.",
        f"No fences {FENCE} inside only at start",
    ],
)
def test_inner_quotes_and_marks_are_untouched(text: str) -> None:
    assert clean_output(tagged(text), ORIGINAL) == text


def test_unclosed_fence_inside_tags_is_kept() -> None:
    body = f"{FENCE}\n{FIXED}"

    assert clean_output(tagged(body), ORIGINAL) == body


@pytest.mark.parametrize("raw", ["", "   \n", tagged(""), tagged("  \n "), tagged('""')])
def test_returns_empty_string_when_nothing_is_left(raw: str) -> None:
    assert clean_output(raw, ORIGINAL) == ""


@pytest.mark.parametrize(
    ("original", "body"),
    [
        ('"To be or not to be."', '"To be or not to be."'),
        ("“Hi there.”", "“Hi there.”"),
        (f"{FENCE}py\nprint(1)\n{FENCE}", f"{FENCE}py\nprint(1)\n{FENCE}"),
        ('  "Padded."  ', '"Padded."'),
    ],
)
def test_wrapper_the_user_wrote_is_kept(original: str, body: str) -> None:
    assert clean_output(tagged(body), original) == body


def test_wrapper_is_still_removed_when_only_the_other_kind_was_in_the_input() -> None:
    assert clean_output(tagged(f'{FENCE}\n"{FIXED}"\n{FENCE}'), f'"{ORIGINAL}"') == f'"{FIXED}"'


def test_single_line_fence_is_removed() -> None:
    assert clean_output(tagged(f"{FENCE}{FIXED}{FENCE}"), ORIGINAL) == FIXED


def test_nested_tags_do_not_survive_cleanup() -> None:
    assert clean_output(tagged(f"{FIXED[:3]}<te<text>xt>{FIXED[3:]}"), ORIGINAL) == FIXED
