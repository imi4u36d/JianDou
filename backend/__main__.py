"""
jiandou CLI - entry point for `python -m app` or `jiandou` command.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def cli():
    """JianDou - AI video generation platform."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8100, type=int, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable hot reload")
@click.option("--skip-build", is_flag=True, help="Skip frontend build")
def serve(host, port, reload, skip_build):
    """Start the FastAPI server (auto-builds frontend)."""
    if not skip_build:
        _build_frontend()
    from backend.config import settings
    import uvicorn
    uvicorn.run("backend.main:app", host=host, port=port, reload=reload)


def _build_frontend() -> None:
    """Build the frontend SPA via Vite."""
    frontend_dir = Path(__file__).resolve().parent.parent / "frontends" / "web"
    if not frontend_dir.is_dir():
        console.print("[yellow]Frontend directory not found, skipping build[/yellow]")
        return
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    console.print("[blue]Building frontend...[/blue]")
    import subprocess
    result = subprocess.run(
        [npm, "run", "build"],
        cwd=str(frontend_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]Frontend build failed:[/red]")
        console.print(result.stderr)
        console.print("[yellow]Continuing with existing static files (if any)[/yellow]")
        return

    # Copy built files to static/web/
    dist_dir = frontend_dir / "dist"
    static_dir = Path(__file__).resolve().parent.parent / "static" / "web"
    static_dir.mkdir(parents=True, exist_ok=True)

    import shutil
    # Remove old static files
    for item in static_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    # Copy new build
    for item in dist_dir.iterdir():
        if item.is_dir():
            shutil.copytree(item, static_dir / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, static_dir / item.name)

    console.print("[green]Frontend built successfully[/green]")


@cli.command()
def init():
    """Initialize the database (create tables)."""
    asyncio.run(_init_db())
    console.print("[green]Database initialized[/green]")


async def _init_db():
    from backend.database import engine, Base
    import backend.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@cli.command()
def seed():
    """Seed the database with default data."""
    asyncio.run(_seed_db())
    console.print("[green]Database seeded[/green]")


async def _seed_db():
    from backend.database import async_session_factory
    from backend.models.user import SysUser
    from backend.models.credit import SysCreditRule, SysCreditAccount
    from backend.auth import hash_password
    from sqlalchemy import select
    from datetime import datetime, timezone

    def _now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    async with async_session_factory() as session:
        # Check if admin exists
        result = await session.execute(select(SysUser).where(SysUser.username == "admin"))
        admin = result.scalar_one_or_none()
        if not admin:
            from backend.config import settings
            now = _now()
            admin = SysUser(
                username=settings.bootstrap_admin_username,
                display_name=settings.bootstrap_admin_display_name,
                password_hash=hash_password(settings.bootstrap_admin_password),
                role="ADMIN",
                status="ACTIVE",
                task_concurrency_limit=1,
                created_at=now,
                updated_at=now,
            )
            session.add(admin)
            await session.flush()
            session.add(SysCreditAccount(
                user_id=admin.id,
                balance=10000,
                total_consumed=0,
                total_adjusted=0,
                created_at=now,
                updated_at=now,
            ))
            session.add(SysCreditRule(feature_code="IMAGE_GENERATION", display_name="图片生成", cost=10, created_at=now, updated_at=now))
            session.add(SysCreditRule(feature_code="VIDEO_GENERATION", display_name="视频生成", cost=50, created_at=now, updated_at=now))
            await session.commit()
            console.print(f"[green]Admin user created: {admin.username} (password: {settings.bootstrap_admin_password})[/green]")
            console.print("[green]Credit rules initialized: IMAGE_GENERATION=10, VIDEO_GENERATION=50[/green]")
            console.print(f"[green]Credit balance: 10000[/green]")
        else:
            console.print("[yellow]Admin user already exists[/yellow]")


@cli.group()
def db():
    """Database management commands."""
    pass


@db.command()
def migrate():
    """Run database migrations."""
    asyncio.run(_init_db())
    console.print("[green]Migrations complete[/green]")


if __name__ == "__main__":
    cli()
