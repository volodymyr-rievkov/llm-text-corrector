# Deploy spec: automatic deployment to HuggingFace Spaces

## Purpose
Host the app (FastAPI backend + Gradio UI, one process) on a free HuggingFace Space so the lab can be
submitted with "a link to the running service". The brief points to HF Spaces as the free hosting option.

## Dependency
Backend and frontend are merged to `master`. The app entrypoint is `llm_text_corrector.main:app` and
listens on one port. `/api/health` returns `{"status": "ok"}`.

## Target
- An HF **Docker** Space (SDK `docker`), port **7860**, the container runs as a non-root user (uid 1000).
- The server holds **no API key and no secrets**. Every user brings their own Groq key in the UI.
- The Space repo needs a `README.md` with front-matter (`title`, `sdk: docker`, `app_port: 7860`), which is
  **generated at deploy time**, so the project README stays clean.

## Container
- Base: `python:3.13-slim`, deps from `uv sync --locked --no-dev`, source from `src/`.
- Start command: uvicorn serving `llm_text_corrector.main:app` on `0.0.0.0:7860`.
- `.dockerignore` excludes `.git`, `.venv`, tests, caches, plans/specs and local env files.
- The image builds from a clean checkout with only `pyproject.toml`, `uv.lock` and `src/`.

## Pipeline
- **On pull request**: the existing checks, plus a job that runs `docker build` (catches a broken image
  before merge). The build job does not push anywhere.
- **On push to `master`** (i.e. after a PR is merged): workflow `deploy.yaml`:
  1. runs the pre-commit checks and the unit and integration tests (reusing the existing workflows through
     `workflow_call`, not copy-pasted);
  2. the coverage gate (unit 100 / integration 95 / combined 100) must pass;
  3. only then the `deploy` job uploads the files to the Space;
  4. it then polls `<space url>/api/health` (with retries) and fails if it never returns 200.
- A failure at any gate means **no deploy**. `concurrency` ensures only the latest deploy runs.
- `workflow_dispatch` is allowed to redeploy manually (it still runs the gates).

## Secrets and variables (set by the user in GitHub, never in code)
- Secret `HF_TOKEN`: HF token with write access to the Space.
- Variable `HF_SPACE_ID`: `<hf-username>/<space-name>`.
Workflows reference them only through `secrets.*` / `vars.*`; they are never echoed.

## Non-functional
- Least-privilege workflow `permissions`. Pin third-party actions by major version, as the existing
  workflows do.
- The deploy is idempotent: the same commit re-deployed gives the same Space contents.
- Only the files the image needs are uploaded to the Space.

## Out of scope
Custom domain, a GPU, a paid tier, persistent storage, a staging Space, rollbacks beyond redeploying an earlier commit.

## Acceptance criteria
1. A local `docker build` and `docker run -p 7860:7860` serves the UI at `/` and `/api/health`.
2. A merge to `master` with all checks green updates the Space, and the health check passes.
3. A merge with a failing check (simulated on a throwaway branch or by the dry run) does not deploy.
4. The public Space URL opens the UI, and a real correction works with the user's own Groq key.
5. The README (or the submission notes) lists the Space URL and the repo link, ready for VNS.
