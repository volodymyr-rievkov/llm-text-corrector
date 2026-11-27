import re

import gradio as gr
import pytest
from gradio.block_function import BlockFunction
from pytest_mock import MockerFixture

from llm_text_corrector.frontend import texts
from llm_text_corrector.frontend.client import BackendClient
from llm_text_corrector.frontend.errors import CorrectionFailedError
from llm_text_corrector.frontend.ui import build_ui, correct_for_ui

API_KEY = "gsk_ui_secret"
TEXT = "I has a apple."
CORRECTED = "I have an apple."
CYRILLIC = re.compile("[а-яіїєґ]", re.IGNORECASE)


@pytest.fixture
def client(mocker: MockerFixture) -> BackendClient:
    mock = mocker.create_autospec(BackendClient, instance=True)
    mock.correct.return_value = CORRECTED
    return mock


@pytest.fixture
def demo(client: BackendClient) -> gr.Blocks:
    return build_ui(client)


def textbox(demo: gr.Blocks, label: str) -> gr.Textbox:
    (found,) = [c for c in demo.blocks.values() if isinstance(c, gr.Textbox) and c.label == label]
    return found


def correct_event(demo: gr.Blocks) -> BlockFunction:
    (found,) = [fn for fn in demo.fns.values() if fn.api_name == "correct"]
    return found


def test_build_ui_returns_blocks(demo: gr.Blocks) -> None:
    assert isinstance(demo, gr.Blocks)


def test_page_has_the_browser_tab_title(demo: gr.Blocks) -> None:
    assert demo.title == texts.PAGE_TITLE


def test_analytics_are_off(demo: gr.Blocks) -> None:
    assert demo.analytics_enabled is False


def test_page_shows_title_and_description(demo: gr.Blocks) -> None:
    markdown = [c.value for c in demo.blocks.values() if isinstance(c, gr.Markdown)]

    assert texts.TITLE in markdown
    assert texts.DESCRIPTION in markdown


def test_key_box_is_a_password_field_with_a_link_to_get_a_key(demo: gr.Blocks) -> None:
    key_box = textbox(demo, texts.KEY_LABEL)

    assert key_box.type == "password"
    assert key_box.info == texts.KEY_INFO


def test_input_box_is_editable(demo: gr.Blocks) -> None:
    assert textbox(demo, texts.INPUT_LABEL).interactive is not False


def test_output_box_is_read_only_with_a_copy_button(demo: gr.Blocks) -> None:
    output = textbox(demo, texts.OUTPUT_LABEL)

    assert output.interactive is False
    assert output.buttons == ["copy"]


def test_page_has_the_correct_button(demo: gr.Blocks) -> None:
    labels = [c.value for c in demo.blocks.values() if isinstance(c, gr.Button)]

    assert labels == [texts.BUTTON_LABEL]


def test_examples_are_listed_and_include_a_non_english_one(demo: gr.Blocks) -> None:
    (dataset,) = [c for c in demo.blocks.values() if isinstance(c, gr.Dataset)]
    examples = [row[0] for row in dataset.samples]

    assert examples == [row[0] for row in texts.EXAMPLES]
    assert 2 <= len(examples) <= 3
    assert any(CYRILLIC.search(example) for example in examples)


async def test_button_runs_the_correction_with_the_client(demo: gr.Blocks, client: BackendClient) -> None:
    callback = correct_event(demo).fn

    assert callback is not None
    assert await callback(TEXT, API_KEY) == CORRECTED
    client.correct.assert_awaited_once_with(TEXT, API_KEY)  # type: ignore[attr-defined]


async def test_correct_for_ui_returns_the_corrected_text(client: BackendClient) -> None:
    assert await correct_for_ui(TEXT, API_KEY, client) == CORRECTED


@pytest.mark.parametrize(
    ("text", "key", "message"),
    [("", API_KEY, texts.MSG_EMPTY_INPUT), (TEXT, "", texts.MSG_ENTER_KEY)],
)
async def test_blank_field_becomes_a_gradio_error_without_a_request(
    client: BackendClient, text: str, key: str, message: str
) -> None:
    with pytest.raises(gr.Error) as caught:
        await correct_for_ui(text, key, client)

    assert caught.value.message == message
    client.correct.assert_not_called()  # type: ignore[attr-defined]


async def test_backend_failure_becomes_a_gradio_error(client: BackendClient) -> None:
    client.correct.side_effect = CorrectionFailedError(texts.MSG_RATE_LIMITED)  # type: ignore[attr-defined]

    with pytest.raises(gr.Error) as caught:
        await correct_for_ui(TEXT, API_KEY, client)

    assert caught.value.message == texts.MSG_RATE_LIMITED


def test_the_button_first_clears_the_previous_answer(demo: gr.Blocks) -> None:
    output = textbox(demo, texts.OUTPUT_LABEL)
    correct = correct_event(demo)
    assert correct.trigger_after is not None
    clear = demo.fns[correct.trigger_after]  # the step the correction waits for

    assert clear.fn is not None
    assert clear.fn() == ""
    assert [block._id for block in clear.outputs] == [output._id]
    assert clear.api_visibility == "private"


def test_users_are_not_queued_behind_each_other(demo: gr.Blocks) -> None:
    assert correct_event(demo).concurrency_limit is None
