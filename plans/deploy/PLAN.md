# Deploy plan: HF Space via GitHub Actions

Branch: `feature/deploy`. Spec: `specs/deploy/SPEC.md`.

## Precondition
Backend and frontend PRs are **merged to `master`**. Run `git fetch && git rebase origin/master` on this
branch. Check that `src/llm_text_corrector/main.py` exposes `app`. If not, stop and tell the user.

## Read first
1. `CLAUDE.md` (overrides this plan), `specs/deploy/SPEC.md`, the existing files in `.github/workflows/`.
2. Check the current docs with context7 or the web: HF Spaces Docker SDK (README front-matter, `app_port`,
   user uid 1000), the `huggingface_hub` CLI upload command (`hf upload` and its flags), `astral-sh/setup-uv`,
   and the Docker image tags available for uv. Don't rely on memory for CLI flags.

## Lab context (for a fresh agent)
Lab 8: an app that makes ONE LLM call and shows only the result; submission via VNS needs the code, a
link to the running service and a short description. Step 3 of 3 (backend → frontend → deploy).

## Manual steps for the user (list them in the PR description, and wait for confirmation)
1. Create a Space on huggingface.co: SDK **Docker**, blank template, public. Note `<user>/<space>`.
2. Create an HF access token with **write** permission.
3. In GitHub → repo settings: add secret `HF_TOKEN` and variable `HF_SPACE_ID`.
The agent never asks for the token value, and never writes it anywhere.

## Step 1: Dockerfile and .dockerignore
- Multi-stage or single stage on `python:3.13-slim`. Copy the `uv` binary from the official uv image, copy
  `pyproject.toml` + `uv.lock` first and run `uv sync --locked --no-dev --no-install-project` (layer cache), then
  copy `src/` and run `uv sync --locked --no-dev`.
- Create a user with uid 1000 and `USER` it; `EXPOSE 7860`; `CMD` runs uvicorn on `0.0.0.0:7860`
  (use the venv's executable, not `uv run` at start-up, to avoid network access at boot).
- `.dockerignore` as in the spec.
- Verify locally: `docker build -t llm-text-corrector .`, then `docker run --rm -p 7860:7860 llm-text-corrector`,
  and check `curl localhost:7860/api/health` and the page at `/`. If Docker isn't available locally, say so and
  rely on the CI build job.

## Step 2: reusable CI
- `pre-commit-checks.yaml` and `python-tests.yaml`: add the `workflow_call:` trigger next to
  `pull_request`. In `pre-commit-checks.yaml` the "run all" step needs a branch for a non-PR event:
  `pre-commit run --all-files` when `github.event_name != 'pull_request'`. Don't change thresholds or the
  existing PR behaviour. The `commit-msg-checks` workflow stays PR-only.
- Add a PR job (new workflow `docker-build.yaml`, or a job in an existing one) that runs
  `docker build` without pushing.

## Step 3: deploy workflow (`.github/workflows/deploy.yaml`)
- Triggers: `push` to `master`, and `workflow_dispatch`.
- `concurrency: { group: deploy, cancel-in-progress: false }`.
- Jobs: `pre-commit` (uses the reusable workflow), `tests` (uses `python-tests.yaml`, which includes the
  coverage gate), then `deploy` with `needs: [pre-commit, tests]` and an `environment` of your choice (only
  if the user wants an approval gate; otherwise none).
- `deploy` job: checkout → install uv / `huggingface_hub` → generate the Space `README.md` front-matter
  into a staging directory → copy in the allow-listed files (`Dockerfile`, `.dockerignore`, `pyproject.toml`,
  `uv.lock`, `.python-version`, `src/`) → `hf upload "$HF_SPACE_ID" <dir> . --repo-type space` with
  `HF_TOKEN` from `secrets` → health-check loop with `curl --retry` against
  `https://<owner>-<space>.hf.space/api/health` (derive the URL from `HF_SPACE_ID`, lowercase, `/` → `-`).
- Pass secrets only through `env:`; never `echo` them, and don't enable `set -x` in steps that use them.
- `permissions: contents: read` for the whole workflow.

## Step 4: verification without risking prod
- Lint the workflows (`actionlint` if available) and run `uv run pre-commit run --all-files`.
- On the PR: the `docker build` job must be green along with all existing checks.
- Dry run: ask the user to confirm the secrets exist, then merge. Watch the `deploy` run with
  `gh run watch` / `gh run list`, and confirm that the Space builds ("Running" status) and the health check
  passes. To test the "failing gate blocks deploy" claim, use a throwaway branch with a deliberately broken
  test and a `workflow_dispatch` run on it. Don't break `master`.
- Ask the user to open the public URL and run one real correction with their own Groq key.

## Step 5: submission notes
Add to `README.md`: what the service does, the Space URL, how to run it locally
(`uv run uvicorn ...`), tests, and the architecture in 5 lines. This is the "short description of the
work done" for VNS. The user submits it themselves; never submit anything on their behalf.

## Definition of done
All checks green on the PR, merge triggers a successful deploy, the health check passes, the Space URL works with a
real key, the README is updated. Report the Space URL to the user.

## Files (checklist)
`Dockerfile`, `.dockerignore`, `.github/workflows/{deploy,docker-build}.yaml`,
`.github/workflows/{pre-commit-checks,python-tests}.yaml` (add `workflow_call`), `README.md`.
