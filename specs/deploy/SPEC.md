# Deploy spec: Render free web service with built-in auto-deploy

## Purpose
Host the app (FastAPI backend + Gradio UI, one process) on a free Render web service so the lab can be
submitted with "a link to the running service".

HuggingFace Docker Spaces were the first choice, but creating one now needs a paid plan, so they are out.
A GitHub Actions deploy workflow was dropped too: Render's own auto-deploy is enough.

## Dependency
Backend and frontend are merged to `master`. The app entrypoint is `llm_text_corrector.main:app` and
listens on one port. `/api/health` returns `{"status": "ok"}`. The `Dockerfile` is on `master`.

## Target
- A Render **Web Service**, Docker runtime, Free instance type, branch `master`, public URL
  `https://llm-text-corrector.onrender.com/`. No payment card is needed.
- The container runs as a non-root user (uid 1000) and listens on **7860**; the service sets `PORT=7860`.
- Health check path on the service: `/api/health`.
- **Auto-deploy is on**: every push to `master` (a merged PR) makes Render rebuild and restart the service.
- The server holds **no API key and no secrets**. Every user brings their own Groq key in the UI.
- Free-tier behaviour to accept: the service sleeps after about 15 minutes idle and takes about a minute to wake.

## Container
- Base: `python:3.13-slim`, deps from `uv sync --locked --no-dev`, source from `src/`.
- Start command: uvicorn serving `llm_text_corrector.main:app` on `0.0.0.0:7860`.
- `.dockerignore` excludes `.git`, `.venv`, tests, caches, plans/specs and local env files.
- The image builds from a clean checkout with `pyproject.toml`, `uv.lock`, `README.md` and `src/`
  (`README.md` is read by the project metadata).

## Pipeline
- **On pull request** (GitHub Actions): pre-commit, unit and integration tests with the coverage gate, commit
  message lint, and a `docker build` job (no push) that catches a broken image before merge.
- **On merge to `master`**: Render builds the image and replaces the running service. There is no deploy
  workflow in GitHub; the PR checks are the quality gate.
- Known limit: Render deploys any push to `master`, even when a check failed, so branch protection
  (required checks) is what keeps a red PR from being merged.

## Secrets and variables
None. GitHub holds no deploy credentials and Render holds no app secrets.

## Non-functional
- Pin third-party actions by major version, as the existing workflows do.
- A redeploy of the same commit gives the same image.

## Out of scope
Custom domain, a GPU, a paid tier, persistent storage, a staging service, rollbacks beyond redeploying an earlier commit.

## Acceptance criteria
1. A local `docker build` and `docker run -p 7860:7860` serves the UI at `/` and `/api/health`.
2. A PR that breaks the image fails the `docker-build` check.
3. After a merge to `master`, Render redeploys and `/api/health` returns 200.
4. The public URL opens the UI, and a real correction works with the user's own Groq key.
5. The README lists the service URL, ready for VNS.
