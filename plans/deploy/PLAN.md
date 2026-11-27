# Deploy plan: Render web service with auto-deploy

Branch: `feature/deploy`. Spec: `specs/deploy/SPEC.md`.

## Status
- Dockerfile and `.dockerignore`: done, merged to `master` in PR #4.
- Render service: created by the user, Docker runtime, Free, `PORT=7860`, health check `/api/health`,
  auto-deploy on. Live at https://llm-text-corrector.onrender.com/ (health returns 200).
- HF Spaces dropped (new Docker Spaces need a paid plan). A GitHub deploy workflow dropped too.

## What this branch still adds
1. `.github/workflows/docker-build.yaml`: PR job that runs `docker build` without pushing.
2. `README.md`: what the service does, the URL, architecture, how to run locally, tests, Docker commands.
3. This plan and the spec.

## Verification
- `uv run pre-commit run --all-files` passes; all PR checks are green, including `docker-build`.
- After the merge, confirm in the Render dashboard that the new deploy is live, and that
  `curl https://llm-text-corrector.onrender.com/api/health` returns 200.
- The user opens the public URL and runs one real correction with their own Groq key.

## Manual follow-ups for the user
- Optional: GitHub branch protection on `master` with the PR checks required, so a red PR can't be merged
  (and so can't trigger a Render deploy).
- Submission via VNS: code, the service link and the short description from the README. The user submits it
  themselves; never submit anything on their behalf.

## Definition of done
PR checks green, merge triggers a successful Render deploy, health check passes, a real correction works,
README updated.
