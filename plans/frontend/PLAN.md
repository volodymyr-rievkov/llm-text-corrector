# Frontend plan: Gradio UI

Branch: `feature/frontend`. Spec: `specs/frontend/SPEC.md`.

## Precondition
The backend PR is **merged to `master`**. Then run `git fetch && git rebase origin/master` (or
`git rebase master`) on this branch, so `src/llm_text_corrector/backend/`, the pytest setup, factories and
`tests/conftest.py` exist. If they don't, stop and tell the user.

## Read first
1. `CLAUDE.md` (it overrides this plan), then `specs/frontend/SPEC.md`, then `plans/backend/PLAN.md` for the
   shared test conventions and commit message rules.
2. Check the current Gradio API with context7: `gr.Blocks`, `gr.Textbox(type="password")`,
   `gr.Examples`, `gr.Warning`/`gr.Error`, `gr.mount_gradio_app`, and the copy button option.

## Lab context (for a fresh agent)
Lab 8: an app that makes ONE LLM call and shows only the result. Step 2 of 3 (backend → frontend →
deploy). The user types a Groq key into the page; the page calls our own backend, which calls Groq.

## Rules
Same as the backend plan: TDD (failing test → minimal code → refactor), mirrored unit tests, integration
tests per pair, factories, `mocker.patch.object`, uv only, reuse before adding, and commitlint-compatible
messages. Never lower coverage thresholds; ask the user if 95 for integration can't be reached.

## Step 0: dependency
`uv add gradio`. Run `uv sync` and commit `uv.lock`. Check that the Gradio version works with the pinned
FastAPI/starlette; if not, report the conflict.

## Step 1: config (`frontend/config.py`)
Tests then `FrontendSettings(BaseSettings)` with `env_prefix="CORRECTOR_"`: `backend_url`,
`request_timeout_s`. Check the defaults and an env override. Reuse the pattern from `backend/config.py`.

## Step 2: backend client (`frontend/client.py`)
- `BackendClient(base_url, timeout, http: httpx.Client | AsyncClient)` with `correct(text, api_key) -> str`.
- Define a small `FrontendError(message)`-style exception hierarchy, or one `CorrectionFailedError` with a
  user-facing message, so the UI layer doesn't parse HTTP itself.
- Unit tests (mock the httpx client): request URL, header `X-Groq-Api-Key`, JSON body; the success parse;
  each error `code` → the message from the spec table; unknown code; non-JSON body; connect/timeout
  errors. Keep the message table in one mapping (single source of truth). Assert the key never appears in
  messages.

## Step 3: handlers (`frontend/handlers.py`)
- `correct_text(text, api_key, client) -> str`: validate blanks first (raise a friendly error without
  calling the client), then call the client. UI-agnostic: raise plain exceptions; the UI adapter converts
  them to `gr.Error`/`gr.Warning`.
- Tests: blank key, blank text (the client is not called, via `assert_not_called`), success, client error
  passes through with its message.

## Step 4: UI (`frontend/ui.py`)
- `build_ui(client) -> gr.Blocks`: title + description (Markdown), password key box, input, button, output
  with copy button, `gr.Examples` (include a Ukrainian one). Wire the button to a thin callback that calls
  `handlers.correct_text` and translates errors into `gr.Error`.
- Keep the text constants (title, description, labels, examples) in one small module (e.g. `frontend/texts.py`)
  so tests can refer to them instead of repeating literals.
- Unit tests: `build_ui()` returns `gr.Blocks`; the expected components exist (find them by type/label);
  the key box has `type="password"`; the callback converts a handler error to `gr.Error`.

## Step 5: entrypoint (`main.py`)
- `create_app() -> FastAPI`: `create_api()` + a `BackendClient` pointed at `FrontendSettings.backend_url` +
  `gr.mount_gradio_app(api, build_ui(client), path="/")`. Expose `app = create_app()` for uvicorn.
- Make sure `/api/*` isn't shadowed by the Gradio root mount.
- Unit test: `create_app()` returns an app with the expected routes (mock `build_ui` if it's slow).

## Step 6: integration tests (pairs)
- `tests/integration/frontend_client_backend_api_test.py`: real `BackendClient` ↔ real backend FastAPI app
  (via `httpx.ASGITransport`, Groq stubbed with `pytest-httpserver` as in the backend tests): success,
  invalid key (401), rate limit (429), and the clean output with an intro-laden stub reply.
- `tests/integration/main_app_test.py`: `create_app()` serves `GET /api/health` → 200 and `GET /` →
  200 with the page title.
- Integration coverage must stay **≥ 95**; if it can't, stop and ask the user.

## Definition of done
```
uv run pre-commit run --all-files
uv run pytest -m unit --cov --cov-fail-under=100
uv run pytest -m integration --cov --cov-fail-under=95
uv run uvicorn llm_text_corrector.main:app --port 7860
```
Open http://127.0.0.1:7860, check the page (description, examples, password field), and ask the user to
paste a real Groq key and try one correction. Never write the key to disk. Take a screenshot with a browser
skill if one is available.
Then open the PR, run `gh pr checks` and fix until all are green. Don't report it ready while CI is red.

## Files (checklist)
`pyproject.toml`, `uv.lock`, `src/llm_text_corrector/main.py`,
`src/llm_text_corrector/frontend/{__init__,config,texts,client,handlers,ui}.py`,
`tests/unit/frontend/*_test.py`, `tests/unit/main_test.py`, `tests/integration/*_test.py`, factories for
backend error payloads in `tests/shared/factories/` if needed (reuse the existing ones first).
