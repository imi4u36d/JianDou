from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/jiandou.db"

    # Server
    server_port: int = 8000
    server_address: str = "0.0.0.0"

    # App
    app_env: str = "dev"
    execution_mode: str = "queue"
    web_origin: str = "http://127.0.0.1:80"
    cookie_secure: bool = False

    # Auth / Security
    secret_key: str = "change-me-to-a-real-secret"
    auth_invite_expiry_hours: int = 12

    # Admin user bootstrap
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_display_name: str = "系统管理员"
    bootstrap_admin_password: str = "admin123"

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

    model_config = {"env_prefix": "JIANDOU_"}

settings = Settings()
