FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:52b32769a56b9fe3350908266099d78852626ea44664ffdc7c12f43f62abb3f8

RUN python3 -m pip install --no-cache-dir uv==0.9.30 \
    && groupadd --system fuzzbuilder \
    && useradd --system --uid 10001 --gid fuzzbuilder --create-home fuzzbuilder \
    && mkdir -p /out /work \
    && chmod 1777 /out /work

ENV UV_PROJECT_ENVIRONMENT=/work/nlm-mcp-venv

COPY --chmod=0555 pyproject.toml uv.lock README.md LICENSE "$SRC/notebooklm-mcp-pro/"
COPY --chmod=0555 src "$SRC/notebooklm-mcp-pro/src"
COPY --chmod=0555 fuzz "$SRC/notebooklm-mcp-pro/fuzz"
COPY --chmod=0555 stubs "$SRC/notebooklm-mcp-pro/stubs"
WORKDIR "$SRC/notebooklm-mcp-pro"
COPY --chmod=0555 .clusterfuzzlite/build.sh "$SRC/build.sh"

USER fuzzbuilder
HEALTHCHECK NONE
