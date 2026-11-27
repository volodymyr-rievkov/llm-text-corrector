"""Gradio page. Callbacks stay thin: the logic lives in `handlers`."""

import gradio as gr

from llm_text_corrector.frontend import texts
from llm_text_corrector.frontend.client import BackendClient
from llm_text_corrector.frontend.errors import FrontendError
from llm_text_corrector.frontend.handlers import correct_text

_INPUT_LINES = 8


async def correct_for_ui(text: str, api_key: str, client: BackendClient) -> str:
    """Run the correction, turning user-facing errors into Gradio alerts."""
    try:
        return await correct_text(text, api_key, client)
    except FrontendError as error:
        raise gr.Error(error.message) from None


def build_ui(client: BackendClient) -> gr.Blocks:
    async def correct(text: str, api_key: str) -> str:
        return await correct_for_ui(text, api_key, client)

    demo = gr.Blocks(title=texts.PAGE_TITLE, analytics_enabled=False)
    with demo:
        gr.Markdown(texts.TITLE)
        gr.Markdown(texts.DESCRIPTION)
        key_box = gr.Textbox(label=texts.KEY_LABEL, type="password", info=texts.KEY_INFO)
        text_box = gr.Textbox(label=texts.INPUT_LABEL, lines=_INPUT_LINES)
        button = gr.Button(texts.BUTTON_LABEL, variant="primary")
        output = gr.Textbox(label=texts.OUTPUT_LABEL, lines=_INPUT_LINES, interactive=False, buttons=["copy"])
        gr.Examples(examples=texts.EXAMPLES, inputs=text_box)
        # Clear first, so a failed request never leaves the previous answer next to the new text.
        # Each user brings their own key, so requests need not wait for each other.
        button.click(lambda: "", outputs=output, api_visibility="private", queue=False).then(
            correct, inputs=[text_box, key_box], outputs=output, api_name="correct", concurrency_limit=None
        )
    return demo
