# syntax=docker/dockerfile:1.9
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.9.30

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-editable

FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL org.opencontainers.image.title="notebooklm-mcp-pro" \
      org.opencontainers.image.description="Production-grade MCP server for Google NotebookLM" \
      org.opencontainers.image.source="https://github.com/oaslananka/notebooklm-mcp-pro" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    NLM_MCP_TRANSPORT=http \
    NLM_MCP_HTTP_HOST=0.0.0.0 \
    NLM_MCP_HTTP_PORT=8080 \
    NLM_MCP_LOG_FORMAT=json

RUN useradd --create-home --uid 10001 --shell /bin/sh appuser

WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app/.venv ./.venv

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"

CMD ["nlm-mcp", "serve"]
