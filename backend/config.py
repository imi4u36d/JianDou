from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings

# Resolve project root from this file's location: backend/config.py → project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_SECRET_KEY = "change-me-to-a-real-secret"
DEFAULT_BOOTSTRAP_ADMIN_PASSWORD = "admin123"


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/jiandou.db"

    # Server
    server_port: int = 8100
    server_address: str = "0.0.0.0"

    # App
    app_env: str = "dev"
    execution_mode: str = "queue"
    web_origin: str = "http://127.0.0.1:80"
    trusted_origins: str = ""
    cookie_secure: bool = False

    # Auth / Security
    secret_key: str = DEFAULT_SECRET_KEY
    auth_invite_expiry_hours: int = 12
    auth_login_rate_limit: int = 10
    auth_invite_activation_rate_limit: int = 5
    auth_rate_limit_window_seconds: int = 60

    # Admin user bootstrap
    bootstrap_admin_username: str = Field(
        default="admin",
        validation_alias=AliasChoices(
            "JIANDOU_BOOTSTRAP_ADMIN_USERNAME",
            "JIANDOU_AUTH_BOOTSTRAP_INITIAL_ADMIN_USERNAME",
        ),
    )
    bootstrap_admin_display_name: str = Field(
        default="系统管理员",
        validation_alias=AliasChoices(
            "JIANDOU_BOOTSTRAP_ADMIN_DISPLAY_NAME",
            "JIANDOU_AUTH_BOOTSTRAP_INITIAL_ADMIN_DISPLAY_NAME",
        ),
    )
    bootstrap_admin_password: str = Field(
        default=DEFAULT_BOOTSTRAP_ADMIN_PASSWORD,
        validation_alias=AliasChoices(
            "JIANDOU_BOOTSTRAP_ADMIN_PASSWORD",
            "JIANDOU_AUTH_BOOTSTRAP_INITIAL_ADMIN_PASSWORD",
        ),
    )

    # Storage
    storage_root: str = "./storage"
    uploads_dir: str = "uploads"
    generation_runs_dir: str = "gen/_runs"
    storage_public_base_url: str = ""
    upload_max_size_bytes: int = 100 * 1024 * 1024  # 100 MB

    # Public URL overrides for frontend build
    public_api_base_url: str = "/api/v3"
    public_storage_base_url: str = "/storage"
    public_admin_base_url: str = "/admin"

    # Task defaults
    source_file_name: str = "text_prompt"
    default_aspect_ratio: str = "16:9"
    default_duration_seconds: int = 8
    editing_mode: str = "drama"
    intro_template: str = "none"
    outro_template: str = "none"

    # Worker / Queue
    generation_async_threads: int = 2
    worker_concurrency: int = 2
    worker_stale_timeout_seconds: int = 30
    worker_poll_interval_ms: int = 1000

    model_config = {
        "env_prefix": "JIANDOU_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def _resolve_relative_paths(self) -> "Settings":
        """Resolve CWD-relative paths against PROJECT_ROOT so the app works
        regardless of which directory it is launched from."""
        # --- storage_root ---
        sr = Path(self.storage_root)
        if not sr.is_absolute():
            self.storage_root = str(PROJECT_ROOT / sr)

        # --- database_url (sqlite path) ---
        for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
            if self.database_url.startswith(prefix):
                db_path = self.database_url[len(prefix):]
                p = Path(db_path)
                if not p.is_absolute():
                    self.database_url = prefix + str(PROJECT_ROOT / p)
                break

        return self

    @property
    def is_production(self) -> bool:
        """True when the app is running in a production-like environment."""
        return self.app_env.lower() in {"prod", "production"}

    @property
    def is_development(self) -> bool:
        """True when the app is running in a development environment."""
        return not self.is_production


class _ValidationIssue:
    """A single configuration validation issue."""

    __slots__ = ("field", "message", "severity")

    def __init__(self, field: str, message: str, severity: str = "error") -> None:
        self.field = field
        self.message = message
        self.severity = severity

    def __str__(self) -> str:
        return f"[{self.severity}] {self.field}: {self.message}"


def validate_settings(s: Settings) -> list[_ValidationIssue]:
    """Return a list of configuration issues for the given settings.

    Unlike ``validate_runtime_settings`` (which raises on blocking issues),
    this returns a full diagnostic list suitable for logging or admin dashboards.
    """
    issues: list[_ValidationIssue] = []

    def _add(field: str, msg: str, severity: str = "warning") -> None:
        issues.append(_ValidationIssue(field, msg, severity))

    # Secret key check
    if not s.secret_key or s.secret_key == DEFAULT_SECRET_KEY:
        if s.is_production:
            _add("secret_key", "must be set to a strong random value in production", "error")
        else:
            _add("secret_key", "using default secret key — change for production", "warning")

    # Admin password check
    if s.bootstrap_admin_password == DEFAULT_BOOTSTRAP_ADMIN_PASSWORD:
        if s.is_production:
            _add("bootstrap_admin_password", "must be changed from the default in production", "error")
        else:
            _add("bootstrap_admin_password", "using default admin password", "warning")

    # Cookie security
    if s.is_production and not s.cookie_secure:
        _add("cookie_secure", "should be true when serving over HTTPS", "error")

    # Web origin sanity
    if not s.web_origin:
        _add("web_origin", "not set — origin-guard checks may break", "warning")

    # Worker concurrency
    if s.worker_concurrency < 1:
        _add("worker_concurrency", "must be at least 1", "error")
    elif s.worker_concurrency > 32:
        _add("worker_concurrency", "high concurrency value may degrade performance", "warning")

    # Poll interval
    if s.worker_poll_interval_ms < 100:
        _add("worker_poll_interval_ms", "very low poll interval may cause excessive database load", "warning")

    # Stale timeout
    if s.worker_stale_timeout_seconds < 5:
        _add("worker_stale_timeout_seconds", "too short — may cause false-positive stale detection", "error")

    # Upload size
    if s.upload_max_size_bytes > 500 * 1024 * 1024:
        _add("upload_max_size_bytes", "upload limit is very high (>500 MB)", "warning")

    return issues


def validate_runtime_settings(s: Settings) -> None:
    """Fail fast for production settings that would be unsafe.

    This is the runtime guard called during startup.  For gentler
    diagnostics use ``validate_settings`` instead.
    """
    issues = validate_settings(s)
    errors = [str(i) for i in issues if i.severity == "error"]

    if errors:
        joined = "; ".join(errors)
        raise RuntimeError(f"Unsafe configuration: {joined}")


settings = Settings()
