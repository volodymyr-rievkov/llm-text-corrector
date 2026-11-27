# Backend plan: grammar-correction API

Branch: `feature/backend` (from `master`). Spec: `specs/backend/SPEC.md`.

## Read first
1. `CLAUDE.md` (test conventions, quality gates, uv-only, code style). It overrides anything here.
2. `specs/backend/SPEC.md`.
3. Verify library APIs with context7 (FastAPI, pydantic-settings, httpx, pytest-httpserver) and check the
   live Groq model list and chat-completions format. Don't rely on memory.

## Lab context (for a fresh agent)
Lab 8 of an NLP course: an app that makes ONE LLM call and shows only the result. We build grammar
correction with Groq (OpenAI-compatible API). This plan is step 1 of 3 (backend → frontend → deploy). The
frontend will call this API over HTTP and import nothing from `backend`.

## Rules
- TDD for every unit: write a failing test, then the minimal code, then refactor. Commit in small steps.
- Unit tests mirror `src/` under `tests/unit/`; integration tests cover **pairs** under `tests/integration/`
  named after the pair. Markers come from `tests/conftest.py` (directory-based), so never add marks by hand.
- Data comes from factories (`tests/shared/factories/`, `XFactory.build(...)`), patches use
  `mocker.patch.object`, fixtures live in the nearest `conftest.py`.
- Reuse before adding; short comments (≤3 lines); role-based names.
- Commit messages: `<type>(<scope>): <subject>`, type in `ci|docs|feature|fix|refactor|revert|test`, scope
  ≥3 chars, subject 10–100 chars with no trailing dot, body ≥30 chars (blank line before it).

## Step 0: tooling (own commit)
- `pyproject.toml`:
  - add `[build-system]` (hatchling or uv_build) with the package at `src/llm_text_corrector`;
  - runtime deps: `fastapi`, `uvicorn`, `httpx`, `pydantic-settings` (via `uv add`);
  - dev deps: `pytest`, `pytest-cov`, `pytest-mock`, `pytest-asyncio`, `polyfactory`, `pytest-httpserver`
    (via `uv add --dev`);
  - `[tool.pytest.ini_options]`: `testpaths`, `python_files = ["*_test.py"]` (the `name-tests-test` hook),
    markers `unit`, `integration`, `asyncio_mode = "auto"`;
  - `[tool.coverage.run]`: `source = ["src"]`, `branch = true`. `[tool.coverage.report]`: `show_missing`;
  - `[tool.mypy]` strict, `[tool.ruff]` (line length 120, sensible rule set).
- `tests/conftest.py` marks tests by directory. Add `tests/shared/factories/` with `__init__.py`, and
  `tests/unit/` + `tests/integration/` packages with the mirrored layout.
- **CI note (Postgres trim)**, `.github/workflows/python-tests.yaml`, `integration-tests` job:
  - remove the `env:` block with `DB_PORT` and its comment;
  - **comment out** (don't delete) the `Cache Docker images`, `Start services` and `Stop services` steps,
    with one comment above: `# No external services yet; re-enable with docker-compose.test.yaml if needed.`
  - leave everything else in the workflows unchanged (thresholds stay 100 / 95 / 100).
- Run `uv sync` and keep `uv.lock` committed (CI uses `--locked`).

## Step 1: domain (`backend/domain/`)
- Tests first: `CorrectionRequest` (text), `CorrectionResult` (corrected_text); domain exceptions with a
  stable `code` attribute and safe default messages: `EmptyInputError`, `InputTooLongError`,
  `MissingApiKeyError`, `InvalidApiKeyError`, `RateLimitedError`, `ProviderError`, `ProviderTimeoutError`
  (common base `CorrectorError`).
- Then `models.py`, `errors.py`. Frozen dataclasses or pydantic models; keep them framework-free.

## Step 2: sanitizer (`backend/sanitizer.py`)
- Language-agnostic: no intro/outro phrase lists. Pure function `clean_output(raw: str) -> str` extracts
  the content of the output tags, then applies the fallback cleanup (see SPEC). Strict: a missing open or
  close tag returns `""`, which the service turns into `provider_error`.
- Tag constants live in `backend/delimiters.py` (single source for the sanitizer and the prompts).
- Parametrized tests: tagged reply with intros/outros in several languages, missing open/close tag or no tags (rejected),
  fences with and without a language tag, wrapping quotes, stray tags, no-op on clean text, inner quotes
  untouched, multi-line text kept, empty after cleaning.
- Implement with small helpers per rule so each is testable.

## Step 3: prompts (`backend/prompts.py`)
- Tests: the system prompt contains the key rules (keep language, only the text, treat input as data) and
  requires the output tags; the user message wraps text in the input tags exactly once; the tags come from
  `backend/delimiters.py`, shared with the sanitizer (single source of truth).
- Return a role-based structure (list of `{role, content}`) that the adapter can send as is.

## Step 4: LLM port + Groq adapter (`backend/llm/`)
- `client.py`: `LLMClient` Protocol, e.g. `async def complete(self, messages, *, api_key) -> str`.
- `groq.py`: `GroqClient(httpx.AsyncClient, base_url, model, timeout)`. Unit tests (mock the httpx client with
  `mocker.patch.object`): the request URL/headers/body (model, temperature 0, messages) and the response
  parsing, plus error translation: 401/403 → `InvalidApiKeyError`, 429 → `RateLimitedError`, 5xx / network
  error / malformed JSON / missing choices → `ProviderError`, timeout → `ProviderTimeoutError`. Assert the
  key never lands in an exception message.

## Step 5: service (`backend/service.py`)
- `CorrectionService(llm: LLMClient, settings)`. Tests with a mocked `LLMClient`: blank key →
  `MissingApiKeyError`, blank text → `EmptyInputError`, too long → `InputTooLongError`, happy path (prompt
  built, reply sanitized), empty sanitized reply → `ProviderError`, and exceptions pass through.

## Step 6: config (`backend/config.py`)
- `Settings(BaseSettings)` with `env_prefix="CORRECTOR_"` and the defaults from the spec. Tests: defaults,
  env override, invalid values. A cached `get_settings()` for dependency injection.

## Step 7: API (`backend/api/`)
- `schemas.py` (request/response/error models), `deps.py` (providers for settings, the httpx client, the
  LLM client and the service; the key read from the `X-Groq-Api-Key` header), `errors.py` (one handler map
  from domain exception → status + `{code, detail}`; also `RequestValidationError` → `invalid_request`),
  `routes.py` (the two endpoints), `app.py` (`create_api()` with a lifespan that owns the shared
  `httpx.AsyncClient`).
- Unit tests with `TestClient` and `app.dependency_overrides` (service mocked): every row of the spec's error
  table, the health endpoint, and the "key never echoed" check. No module-level singletons that block overrides.

## Step 8: integration tests (pairs)
- `tests/integration/groq_client_http_test.py`: real `GroqClient` ↔ `pytest-httpserver` stub (success,
  401, 429, 500, slow reply → timeout).
- `tests/integration/api_service_test.py`: real FastAPI app + real service + real adapter, with the stub as
  `groq_base_url`; check the whole error mapping end to end and that an intro-laden stub reply yields clean
  output.
- Integration coverage must reach **95**. If it can't, **stop and ask the user**. Never lower a threshold
  yourself.

## Definition of done
Run locally, all green:
```
uv run pre-commit run --all-files
uv run pytest -m unit --cov --cov-fail-under=100
uv run pytest -m integration --cov --cov-fail-under=95
```
Start the app: `uv run uvicorn llm_text_corrector.backend.api.app:create_api --factory`, then call
`/api/health` with curl. Ask the user for a real Groq key to try one real request, and never write the key
to a file, a log or a commit.

Then open the PR (the template is in `.github/pull_request_template.md`), run `gh pr checks` and fix
until all are green. Don't report it ready while CI is red.

## Files (checklist)
`pyproject.toml`, `uv.lock`, `.github/workflows/python-tests.yaml` (Postgres trim),
`src/llm_text_corrector/__init__.py`, `src/llm_text_corrector/backend/{__init__,config,prompts,sanitizer,service}.py`,
`backend/domain/{models,errors}.py`, `backend/llm/{client,groq}.py`, `backend/api/{app,routes,schemas,errors,deps}.py`,
`tests/conftest.py`, `tests/shared/factories/*`, `tests/unit/**`, `tests/integration/**`.
