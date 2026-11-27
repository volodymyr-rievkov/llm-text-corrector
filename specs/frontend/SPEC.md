# Frontend spec: Gradio UI for the grammar-correction API

## Purpose
A lightweight web page where a user pastes a Groq API key and a text, presses a button and sees only the
corrected text. It is the UI of a university lab project ("LLM project, basic"). The brief recommends
Gradio/Streamlit, a short description of the service on the page, and an API-key field so the key is
not stored in code.

## Dependency on the backend
Requires the backend from `specs/backend/SPEC.md` (merged to `master`). The frontend talks to it **only
over the HTTP contract** (`POST /api/v1/corrections`, header `X-Groq-Api-Key`; in-process by default) and **never imports** from
`llm_text_corrector.backend`. Errors arrive as `{"code", "detail"}`.

## Page content
- Title and a 2–3 sentence description (what it does; the key is used for one request and not stored;
  works with Groq).
- API key field: password type, label "Groq API key", with a link to get a key.
- Input text area ("Text to correct") and a "Correct" button.
- Output text area ("Corrected text") that is read-only, with a copy button.
- 2–3 examples (short texts with obvious mistakes; at least one non-English, e.g. Ukrainian).
- UI language: English.

## Behaviour
- Empty/whitespace key or text → a friendly warning (`gr.Warning` or `gr.Error`) and **no HTTP request**.
- The key is trimmed before sending (pasted keys often carry a trailing space or newline). A key that cannot
  travel in an HTTP header (non-ASCII, inner whitespace, control characters) → "Check your Groq API key."
  and **no HTTP request**.
- Success → the corrected text appears in the output.
- Backend error codes map to clear user messages:

| code | message idea |
|---|---|
| `missing_api_key`, `invalid_api_key` | Check your Groq API key. |
| `empty_input` | Enter some text first. |
| `input_too_long` | The text is too long; shorten it. (Show the limit if the backend gives it.) |
| `rate_limited` | Groq rate limit reached; wait a minute and retry. |
| `provider_error` | Groq had a problem; try again. |
| `provider_timeout` | Groq took too long; try again. |
| unknown code / non-JSON / network failure to the backend | Generic "Something went wrong" message. |

- While the request runs the button shows progress; the UI never shows stack traces.
- The key is never echoed into the output, logs or error messages.

## Mounting
`llm_text_corrector.main:create_app()` builds the backend app, mounts the Gradio UI at `/`
(`gr.mount_gradio_app`) and returns one ASGI app: UI at `/`, API at `/api/...`, as one process on one port.
The UI reaches the API through `CORRECTOR_BACKEND_URL`. Unset (the default), it calls the API in the same
process through an ASGI transport, so it works on any port and needs no network hop. Set, it calls that URL
over real HTTP. The HTTP client the UI uses is closed when the app shuts down.
Local run: `uv run uvicorn llm_text_corrector.main:app --port 8000` (with `app = create_app()` exposed).

## Configuration
Environment prefix `CORRECTOR_`: `BACKEND_URL` (optional, an http(s) URL), `REQUEST_TIMEOUT_S` (default a bit above the backend's
timeout, so the backend answers first).

## Non-functional
- Python 3.13, `src/` layout, typed, ruff and mypy clean.
- Logic stays out of the Gradio callbacks: UI code is thin and handlers are UI-agnostic and testable.
- No real Groq call in tests.

## Acceptance criteria
1. Every row of the message table is covered by a unit test.
2. An integration test sends a request through the frontend client to the real backend app (Groq stubbed)
   and gets the corrected text; another test checks that `create_app()` serves both `/api/health` and
   the Gradio page.
3. Empty key/text sends no request (asserted).
4. CI green with the existing coverage gates (unit 100, integration 95, combined 100).
