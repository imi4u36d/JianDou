# syntax=docker/dockerfile:1.7

FROM python:3.12-slim

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN rm -f /etc/apt/apt.conf.d/docker-clean
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends build-essential ffmpeg curl

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install uv

COPY pyproject.toml uv.lock README.md License ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY alembic.ini ./
COPY backend/ backend/
COPY config/ config/
COPY migrations/ migrations/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

RUN mkdir -p /app/data /app/storage/uploads /app/storage/outputs /app/storage/temp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/v3/ready >/dev/null || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "backend.main:app"]
