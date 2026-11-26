# CLAUDE.md

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
  config values) in them; point to the relevant `specs/*.md` instead.
  Those values change, and hunting down every comment that quoted them is
  wasted churn.
- Names: prefer generic, role-based function/variable names over ones that encode
  the current implementation detail, so a small logic change doesn't force a rename.