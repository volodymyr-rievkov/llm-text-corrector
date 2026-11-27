# LLM Text Corrector

A small web app that fixes grammar and spelling in a text with ONE call to an LLM (Groq) and shows only the
corrected result. Each user enters their own Groq API key in the page; the server stores no keys.

**Live service:** https://llm-text-corrector.onrender.com/ (free hosting: after about 15 minutes idle it sleeps, and the first request takes about a minute)

## Architecture
- One FastAPI process: the API lives under `/api`, the Gradio page is mounted at `/`.
- `backend/`: `api` (routes, schemas, errors), `service` (builds the prompt and calls the LLM),
  `llm` (Groq client), `sanitizer` and `delimiters` (clean the input and output).
- `frontend/`: the Gradio UI, with a small client that calls the API (in the same process by default).
- Settings come from `CORRECTOR_*` variables (see `.env.example`).
- Deploy: pull requests must pass the GitHub checks and tests; Render rebuilds the Docker image from `master` after each merge.

## Run locally
```
uv sync
uv run uvicorn llm_text_corrector.main:app --port 8000
```
Open http://127.0.0.1:8000 and paste your Groq API key in the page.

## Tests
```
uv run pytest -m unit
uv run pytest -m integration
```

## Docker
```
docker build -t llm-text-corrector .
docker run --rm -p 7860:7860 llm-text-corrector
```
