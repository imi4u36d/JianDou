from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

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


def validate_runtime_settings(settings: Settings) -> None:
    """Fail fast for production settings that would be unsafe in the open."""
    if settings.app_env.lower() not in {"prod", "production"}:
        return

    errors: list[str] = []
    if settings.secret_key == DEFAULT_SECRET_KEY:
        errors.append("set JIANDOU_SECRET_KEY to a strong random value")
    if settings.bootstrap_admin_password == DEFAULT_BOOTSTRAP_ADMIN_PASSWORD:
        errors.append("set JIANDOU_BOOTSTRAP_ADMIN_PASSWORD before enabling prod")
    if not settings.cookie_secure:
        errors.append("set JIANDOU_COOKIE_SECURE=true when serving over HTTPS")

    if errors:
        joined = "; ".join(errors)
        raise RuntimeError(f"Unsafe production configuration: {joined}.")


settings = Settings()
