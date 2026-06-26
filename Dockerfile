FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock alembic.ini ./
COPY backend/ backend/
COPY config/ config/
COPY migrations/ migrations/
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

RUN pip install --no-cache-dir .
RUN chmod +x /app/docker-entrypoint.sh

RUN mkdir -p /app/data /app/storage/uploads /app/storage/outputs /app/storage/temp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/v3/ready >/dev/null || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "backend.main:app"]
