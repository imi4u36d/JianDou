# Configuration Reference

JianDou reads environment variables with the `JIANDOU_` prefix. Start from one of the checked-in templates:

- `.env.dev.example` for local source development.
- `.env.docker.example` for the Docker quick start.
- `.env.prod.example` for production deployments.

Do not commit copied `.env` files or `config/model/providers.secrets.yml`.

## Validation

The `Settings` class provides two levels of validation:

- `validate_runtime_settings(settings)` — called at startup; raises `RuntimeError` for
  blocking issues (e.g. default secret key in production).
- `validate_settings(settings)` — returns a list of `_ValidationIssue` objects with
  severity levels (`error` / `warning`), suitable for logging or admin dashboards.
- `settings.is_production` and `settings.is_development` are convenience properties
  on the `Settings` instance.

## App And Server

- `JIANDOU_APP_ENV`: `dev`, `prod`, or `production`. Production mode fails fast when unsafe defaults are used.
- `JIANDOU_EXECUTION_MODE`: task execution mode, normally `queue`.
- `JIANDOU_SERVER_ADDRESS`: bind address used by the CLI/container entrypoint.
- `JIANDOU_SERVER_PORT`: bind port used by the CLI/container entrypoint. In Docker Compose this is the backend-internal port (`8000`); the public web entrypoint is the `frontend` service on host port `8100`.
- `JIANDOU_AUTO_MIGRATE`: Docker entrypoint flag; `true` runs Alembic migrations on startup.
- `JIANDOU_STARTUP_WAIT_SECONDS`: Docker entrypoint timeout for waiting until configured database/Redis sockets are reachable before migrations run.
- `JIANDOU_STARTUP_RETRIES`: Docker entrypoint retry count for startup migration and seed commands.
- `JIANDOU_STARTUP_RETRY_DELAY_SECONDS`: delay between Docker entrypoint migration/seed retry attempts.

## Docker Compose Topology

The Docker deployment runs the web UI and backend as separate containers:

- `frontend`: Nginx container exposed on `http://127.0.0.1:8100`; serves the Vue SPA and proxies backend paths.
- `app`: FastAPI / worker container on the internal Compose network at `app:8000`; runs migrations and seed data on startup.
- `mysql` and `redis`: stateful backing services using named Docker volumes.

The frontend gateway proxies `/api/`, `/storage/`, and `/runtime-config.json` to `app:8000`, so browser requests remain same-origin at `:8100`.

## Database

- `JIANDOU_DATABASE_URL`: async SQLAlchemy URL. SQLite works out of the box, for example `sqlite+aiosqlite:///./data/jiandou.db`.
- `JIANDOU_DB_POOL_SIZE`: SQLAlchemy pool size for non-SQLite databases.
- `JIANDOU_DB_MAX_OVERFLOW`: additional connections allowed beyond the pool size.
- `JIANDOU_DB_POOL_TIMEOUT`: seconds to wait for a pooled connection.
- `JIANDOU_DB_POOL_RECYCLE`: seconds before recycling pooled connections.

For Docker Compose / MySQL deployments, use `mysql+asyncmy://jiandou:jiandou@mysql:3306/jiandou?charset=utf8mb4`.

## Redis And Cache

- `JIANDOU_REDIS_URL`: Redis connection URL, for example `redis://redis:6379/0`.
- `JIANDOU_RATE_LIMIT_BACKEND`: `memory` or `redis`; Redis is recommended for multi-worker deployments.
- `JIANDOU_CACHE_BACKEND`: `memory` or `redis`; Redis enables short TTL API response caching.
- `JIANDOU_TASK_LIST_CACHE_TTL_SECONDS`: TTL for user task-list cache entries.
- `JIANDOU_TASK_TRACE_CACHE_TTL_SECONDS`: TTL for task trace cache entries.

## Web, Cookies, And Public URLs

- `JIANDOU_WEB_ORIGIN`: canonical frontend origin used for trusted state-changing API requests.
- `JIANDOU_TRUSTED_ORIGINS`: comma-separated additional frontend origins.
- `JIANDOU_COOKIE_SECURE`: set to `true` when serving over HTTPS.
- `JIANDOU_PUBLIC_API_BASE_URL`: public API base path exposed to the frontend. Keep `/api/v3` for the default frontend gateway.
- `JIANDOU_PUBLIC_STORAGE_BASE_URL`: public storage path exposed to the frontend. Keep `/storage` for the default frontend gateway.
- `JIANDOU_PUBLIC_ADMIN_BASE_URL`: public admin path exposed to the frontend. Keep `/admin` for the default frontend gateway.
- `JIANDOU_STORAGE_PUBLIC_BASE_URL`: absolute public storage origin when storage is served outside the app.

## Auth And Security

- `JIANDOU_SECRET_KEY`: signing/encryption secret. Generate a strong random value for production.
- `JIANDOU_BOOTSTRAP_ADMIN_USERNAME`: bootstrap admin username.
- `JIANDOU_BOOTSTRAP_ADMIN_PASSWORD`: bootstrap admin password. Change before production.
- `JIANDOU_AUTH_INVITE_EXPIRY_HOURS`: default invite expiry window.
- `JIANDOU_AUTH_LOGIN_RATE_LIMIT`: login attempts per limiter window.
- `JIANDOU_AUTH_INVITE_ACTIVATION_RATE_LIMIT`: invite activation attempts per limiter window.
- `JIANDOU_AUTH_RATE_LIMIT_WINDOW_SECONDS`: limiter window size.

## Storage

- `JIANDOU_STORAGE_ROOT`: local storage root.
- `JIANDOU_STORAGE_BACKEND`: storage backend for uploads and generated artifacts. Use `local` for filesystem storage or `aliyun_oss` for Alibaba Cloud OSS.
- `JIANDOU_UPLOADS_DIR`: upload directory below the storage root.
- `JIANDOU_GENERATION_RUNS_DIR`: generation run directory below the storage root.
- `JIANDOU_UPLOAD_MAX_SIZE_BYTES`: maximum upload file size in bytes (default: 104857600, i.e. 100 MB).
- `JIANDOU_ALIYUN_OSS_ENDPOINT`: OSS endpoint, for example `https://oss-cn-hangzhou.aliyuncs.com`.
- `JIANDOU_ALIYUN_OSS_BUCKET`: OSS bucket name, for example `jiandouai`.
- `JIANDOU_ALIYUN_OSS_ACCESS_KEY_ID`: AccessKey ID used for OSS uploads.
- `JIANDOU_ALIYUN_OSS_ACCESS_KEY_SECRET`: AccessKey secret used for OSS uploads.
- `JIANDOU_ALIYUN_OSS_SECURITY_TOKEN`: optional STS security token for temporary credentials.
- `JIANDOU_ALIYUN_OSS_KEY_PREFIX`: optional object key prefix, useful for separating environments in one bucket.

## Worker And Queue

- `JIANDOU_GENERATION_ASYNC_THREADS`: model generation helper thread count.
- `JIANDOU_WORKER_CONCURRENCY`: concurrent worker task count.
- `JIANDOU_WORKER_STALE_TIMEOUT_SECONDS`: stale worker claim timeout.
- `JIANDOU_WORKER_POLL_INTERVAL_MS`: queue polling interval.

## Logging

- `JIANDOU_LOG_JSON_FORMAT`: set to `true` to emit JSON structured logs.

## Task Defaults

- `JIANDOU_SOURCE_FILE_NAME`: fallback name for prompt-only tasks.
- `JIANDOU_DEFAULT_ASPECT_RATIO`: default generation aspect ratio.
- `JIANDOU_DEFAULT_DURATION_SECONDS`: default video duration.
- `JIANDOU_EDITING_MODE`: default editing mode.
- `JIANDOU_INTRO_TEMPLATE`: default intro template key.
- `JIANDOU_OUTRO_TEMPLATE`: default outro template key.

## Model Provider Secrets

Platform-wide provider keys should normally live in `config/model/providers.secrets.yml`, copied from `config/model/providers.secrets.example.yml`.

Optional environment overrides:

- `JIANDOU_MODEL_API_KEY`
- `JIANDOU_MODEL_BASE_URL`
