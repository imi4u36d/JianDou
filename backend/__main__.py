"""
jiandou CLI - entry point for `python -m backend` or `jiandou` command.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC
from pathlib import Path

import click
from rich.console import Console

from backend.logging_config import configure_logging

console = Console()


@click.group()
def cli():
    """JianDou - AI video generation platform."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8100, type=int, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable hot reload")
def serve(host, port, reload):
    """Start the FastAPI server."""
    from backend.config import settings

    configure_logging(level=logging.INFO, json_format=settings.log_json_format)

    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@cli.command()
def init():
    """Initialize or upgrade the database."""
    _run_migrations()
    console.print("[green]Database initialized[/green]")


@cli.command()
@click.option(
    "--output",
    "-o",
    default="docs/openapi.json",
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to write the generated OpenAPI schema.",
)
def openapi(output: Path):
    """Export the FastAPI OpenAPI schema without starting the server."""
    from backend.main import create_app

    app = create_app(start_worker=False)
    schema = app.openapi()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    console.print(f"[green]OpenAPI schema written to {output}[/green]")


@cli.command()
def seed():
    """Seed the database with default data."""
    asyncio.run(_seed_db())
    console.print("[green]Database seeded[/green]")


async def _seed_db():
    from datetime import datetime

    from sqlalchemy import select

    from backend.auth import hash_password
    from backend.database import async_session_factory
    from backend.models.credit import SysCreditAccount, SysCreditRule
    from backend.models.user import SysUser

    def _now() -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    async with async_session_factory() as session:
        # Check if admin exists
        result = await session.execute(select(SysUser).where(SysUser.username == "admin"))
        admin = result.scalar_one_or_none()
        if not admin:
            from backend.config import settings

            now = _now()
            admin = SysUser(
                username=settings.bootstrap_admin_username,
                password_hash=hash_password(settings.bootstrap_admin_password),
                role="ADMIN",
                status="ACTIVE",
                task_concurrency_limit=1,
                created_at=now,
                updated_at=now,
            )
            session.add(admin)
            await session.flush()
            session.add(
                SysCreditAccount(
                    user_id=admin.id,
                    balance=10000,
                    total_consumed=0,
                    total_adjusted=0,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                SysCreditRule(
                    feature_code="IMAGE_GENERATION", display_name="图片生成", cost=10, created_at=now, updated_at=now
                )
            )
            session.add(
                SysCreditRule(
                    feature_code="VIDEO_GENERATION", display_name="视频生成", cost=50, created_at=now, updated_at=now
                )
            )
            await session.commit()
            console.print(f"[green]Admin user created: {admin.username}[/green]")
            console.print("[green]Credit rules initialized: IMAGE_GENERATION=10, VIDEO_GENERATION=50[/green]")
            console.print("[green]Credit balance: 10000[/green]")
        else:
            console.print("[yellow]Admin user already exists[/yellow]")


@cli.group()
def db():
    """Database management commands."""
    pass


@db.command()
def migrate():
    """Run database migrations."""
    _run_migrations()
    console.print("[green]Migrations complete[/green]")


@db.command()
def current():
    """Show the current database migration revision."""
    from alembic import command
    from alembic.config import Config

    command.current(Config("alembic.ini"))


@db.command()
def history():
    """Show database migration history."""
    from alembic import command
    from alembic.config import Config

    command.history(Config("alembic.ini"))


def _run_migrations() -> None:
    """Run Alembic migrations.

    Handles the case where tables already exist (e.g. created by
    ``Base.metadata.create_all``) but the ``alembic_version`` table
    has not been stamped yet.  In that situation we stamp to the
    current head first, then run a normal upgrade so any future
    incremental migrations will still apply.
    """
    import sqlite3

    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config("alembic.ini")
    script_dir = ScriptDirectory.from_config(cfg)
    head = script_dir.get_current_head()
    if not head:
        console.print("[yellow]No migration revisions found, nothing to do.[/yellow]")
        return

    # Determine the database path for SQLite stamp detection.
    from backend.config import settings

    db_url = settings.database_url
    db_path: str | None = None
    if db_url.startswith("sqlite+aiosqlite:///"):
        db_path = db_url.split("///", 1)[1]
    elif db_url.startswith("sqlite:///"):
        db_path = db_url.split("///", 1)[1]

    need_stamp = False
    if db_path and Path(db_path).exists():
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
            has_version_table = cursor.fetchone() is not None
            conn.close()
            if not has_version_table:
                need_stamp = True
        except Exception:
            need_stamp = True

    if need_stamp:
        console.print("[yellow]Tables exist but alembic_version is missing; stamping to current head...[/yellow]")
        command.stamp(cfg, "head")

    command.upgrade(cfg, "head")


if __name__ == "__main__":
    cli()
