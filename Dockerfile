FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Non-root user (uid 1000), as required by HF Spaces.
RUN useradd --create-home --uid 1000 app
USER app
WORKDIR /home/app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/home/app/.venv/bin:$PATH"

# Dependencies first, for layer caching. README.md is needed by the project metadata.
COPY --chown=app pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY --chown=app src ./src
RUN uv sync --locked --no-dev

EXPOSE 7860
CMD ["uvicorn", "llm_text_corrector.main:app", "--host", "0.0.0.0", "--port", "7860"]
