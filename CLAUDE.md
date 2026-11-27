# CLAUDE.md

# Development workflow: always TDD
- **Write the test first, for every code change** (feature, bug fix, refactor with a behavior change). Order:
  1. **Red:** write the failing test(s) and run them. Confirm they fail for the right reason.
  2. **Green:** write the smallest code that makes them pass.
  3. **Refactor:** clean up with the tests green.
- **A bug fix starts with a regression test** that reproduces the bug and fails before the fix.
- **Never lose a test case.** Don't delete or weaken an existing test to make a change pass. If a requirement
  changes, update the test and the spec in the same change, and say so.
- **Cover every branch and edge case** of the change (empty, boundary, error and "other kind" inputs), not only
  the happy path. Coverage thresholds in CI are a floor, not the goal.
- In the final report, state which tests were added or changed, and that they were seen failing first.

# Test conventions:
- **Unit tests mirror the project structure.** `tests/unit/` has the same layout as the source tree: the tests
  for `src/<pkg>/<module>.py` live in `tests/unit/<pkg>/<module>_test.py`.
- **Integration tests cover pairs of components.** Each one exercises a single real interaction between two
  components (e.g. A calling B), not the whole system. Name them after the pair under `tests/integration/`.
- **Markers come from the directory.** `tests/conftest.py` marks everything under `tests/unit/` as `unit` and
  `tests/integration/` as `integration`. Don't add `@pytest.mark.unit`/`pytestmark`.
- **Data comes from factories** (`tests/shared/factories/`), always called as `XFactory.build(...)`. Use a
  literal only when the literal is the thing being asserted (a wire format, a dedup key, a bucket name); else
  refer to the built object (`collection.code`).
- **Patch with `mocker.patch.object(...)`,** never `@mock.patch` decorators. Reusable mocks live in
  `tests/unit/mocks.py` (`paginated`, `mock_jetstream`, `mock_nats_msg`, `mock_nats_client`) — unit-only;
  integration tests use the real services. `tests/shared/` holds only what both use: factories and constants.
- **Fixtures live in the nearest `conftest.py`;** `*_test.py` files hold only tests.

# Quality gates (every PR)

Every PR must pass the pre-commit checks and the unit + integration tests, both locally before the PR is
opened and on GitHub (CI) after.

- **Before opening a PR (locally):** run `uv run pre-commit run --all-files`, then `uv run pytest -m unit` and
  `uv run pytest -m integration`. Fix every failure first. Don't open the PR, or use `--no-verify`, while
  anything is red.
- **After opening the PR (GitHub):** check the workflow runs with `gh pr checks` (or `gh run list/view`). If a
  check fails, fix it, push and re-check until all are green. Don't report the PR as ready while CI is red.
- Coverage thresholds are enforced in CI; see `.github/workflows/` for the current values.
- **After every push to a PR,** run `gh pr checks <number> --watch` until it finishes and report the result.
  Never leave it at "checks pending", and never assume CI is green.
- **Keep `.env.example` in sync with the settings.** Every `CORRECTOR_*` variable that a settings class reads
  (`backend/config.py`, `frontend/config.py`, any new one) must appear in `.env.example` with its default and
  a one-line note. Add, rename or remove it there in the same change as the setting, and update the matching
  spec. Before opening a PR, compare the settings fields with `.env.example`.
- **PR description:** build it from `.github/pull_request_template.md`. Keep every heading and checklist as
  is (checkboxes unticked) and write the summary under "Technical implementation details". Don't write the
  body from scratch.

# Plans and specs

- **Plans** live in `plans/<feature-name>/PLAN.md`.
- **Specs** live in `specs/<feature-name>/SPEC.md`.
- `<feature-name>` is a short kebab-case name, the same for a feature's plan and spec.
- Don't put plans or specs elsewhere (no loose `plan.md`/`spec.md`).

# Python Environment & Package Management with uv

Use uv exclusively for all Python actions in this project. 

## Strict Rules
- Never use pip, pip-tools, poetry, virtualenv, or conda.
- Always check for a `uv.lock` before performing operations.
- Do not attempt to manually source `.venv/bin/activate`.

## Approved Commands
- Install dependencies: `uv add <package>`
- Remove dependencies: `uv remove <package>`
- Synchronize environment: `uv sync`
- Running scripts/tools: `uv run <script.py>` or `uv run pytest`

# Code style

- **Reuse before adding.** Before adding a constant, fixture, factory, mock, helper or similar, search for an
  existing one. Don't copy-paste it or create a duplicate. Import it from a single source of truth, and move it
  to a shared place (e.g. `tests/shared/`) if a second consumer needs it. Keep a separate copy only when
  sharing would make no sense.

- Comments/docstrings: brief, ~3 lines max — orientation, not rationale. Never
  hardcode volatile specifics (table/schema names, PRD decision numbers,
  config values) in them; point to the relevant `specs/<feature-name>/SPEC.md` instead.
  Those values change, and hunting down every comment that quoted them is
  wasted churn.
- Names: prefer generic, role-based function/variable names over ones that encode
  the current implementation detail, so a small logic change doesn't force a rename.