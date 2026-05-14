# syntax=docker/dockerfile:1.9
FROM ghcr.io/astral-sh/uv@sha256:538e0b39736e7feae937a65983e49d2ab75e1559d35041f9878b7b7e51de91e4 AS uv

FROM python@sha256:401f6e1a67dad31a1bd78e9ad22d0ee0a3b52154e6bd30e90be696bb6a3d7461 AS builder

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

FROM python@sha256:401f6e1a67dad31a1bd78e9ad22d0ee0a3b52154e6bd30e90be696bb6a3d7461 AS runtime

LABEL org.opencontainers.image.title="notebooklm-mcp-pro" \
      org.opencontainers.image.description="Production-grade MCP server for Google NotebookLM" \
      org.opencontainers.image.source="https://github.com/oaslananka/notebooklm-mcp-pro" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="1.0.2"

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
