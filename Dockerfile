FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY backend/__init__.py backend/__init__.py
RUN pip install --no-cache-dir .

COPY backend/ backend/
COPY static/ static/
COPY config/ config/

RUN mkdir -p /app/data /app/storage/uploads /app/storage/outputs /app/storage/temp

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
