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
- `JIANDOU_SERVER_PORT`: bind port used by the CLI/container entrypoint.
- `JIANDOU_AUTO_MIGRATE`: Docker entrypoint flag; `true` runs Alembic migrations on startup.

## Database

- `JIANDOU_DATABASE_URL`: async SQLAlchemy URL. SQLite works out of the box, for example `sqlite+aiosqlite:///./data/jiandou.db`.

## Web, Cookies, And Public URLs

- `JIANDOU_WEB_ORIGIN`: canonical frontend origin used for trusted state-changing API requests.
- `JIANDOU_TRUSTED_ORIGINS`: comma-separated additional frontend origins.
- `JIANDOU_COOKIE_SECURE`: set to `true` when serving over HTTPS.
- `JIANDOU_PUBLIC_API_BASE_URL`: public API base path exposed to the frontend.
- `JIANDOU_PUBLIC_STORAGE_BASE_URL`: public storage path exposed to the frontend.
- `JIANDOU_PUBLIC_ADMIN_BASE_URL`: public admin path exposed to the frontend.
- `JIANDOU_STORAGE_PUBLIC_BASE_URL`: absolute public storage origin when storage is served outside the app.

## Auth And Security

- `JIANDOU_SECRET_KEY`: signing/encryption secret. Generate a strong random value for production.
- `JIANDOU_BOOTSTRAP_ADMIN_USERNAME`: bootstrap admin username.
- `JIANDOU_BOOTSTRAP_ADMIN_DISPLAY_NAME`: bootstrap admin display name.
- `JIANDOU_BOOTSTRAP_ADMIN_PASSWORD`: bootstrap admin password. Change before production.
- `JIANDOU_AUTH_INVITE_EXPIRY_HOURS`: default invite expiry window.
- `JIANDOU_AUTH_LOGIN_RATE_LIMIT`: login attempts per limiter window.
- `JIANDOU_AUTH_INVITE_ACTIVATION_RATE_LIMIT`: invite activation attempts per limiter window.
- `JIANDOU_AUTH_RATE_LIMIT_WINDOW_SECONDS`: limiter window size.

## Storage

- `JIANDOU_STORAGE_ROOT`: local storage root.
- `JIANDOU_UPLOADS_DIR`: upload directory below the storage root.
- `JIANDOU_GENERATION_RUNS_DIR`: generation run directory below the storage root.
- `JIANDOU_UPLOAD_MAX_SIZE_BYTES`: maximum upload file size in bytes (default: 104857600, i.e. 100 MB).

## Worker And Queue

- `JIANDOU_GENERATION_ASYNC_THREADS`: model generation helper thread count.
- `JIANDOU_WORKER_CONCURRENCY`: concurrent worker task count.
- `JIANDOU_WORKER_STALE_TIMEOUT_SECONDS`: stale worker claim timeout.
- `JIANDOU_WORKER_POLL_INTERVAL_MS`: queue polling interval.

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
