from __future__ import annotations

import os
import subprocess

import pytest

pytestmark = pytest.mark.integration
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_TRACKED_FILES = {
    "config/model/providers.secrets.yml",
    "static/web/index.html",
}

FORBIDDEN_TRACKED_PREFIXES = (
    "build/",
    "dist/",
    "node_modules/",
    "static/web/assets/",
)

FORBIDDEN_TRACKED_SUFFIXES = (
    ".db",
    ".egg-info/PKG-INFO",
)


def test_repository_does_not_track_local_runtime_or_build_outputs() -> None:
    tracked_existing_files = _tracked_existing_files()
    forbidden = [
        path
        for path in tracked_existing_files
        if _is_forbidden_tracked_file(path)
    ]

    assert forbidden == []


def test_secret_template_uses_placeholders_only() -> None:
    template = REPO_ROOT / "config/model/providers.secrets.example.yml"

    assert template.is_file()
    assert "sk-" not in template.read_text(encoding="utf-8")


def test_docker_runtime_configuration_is_documented_consistently() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = (REPO_ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")
    env_example = (REPO_ROOT / ".env.docker.example").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert 'CMD ["uvicorn", "backend.main:app"]' in dockerfile
    assert "--port \"${JIANDOU_SERVER_PORT:-8000}\"" in entrypoint
    assert "JIANDOU_SERVER_PORT=8000" in env_example
    assert "docker run -d -p 8100:8000" in readme


def test_release_check_runs_all_release_facing_gates() -> None:
    script = (REPO_ROOT / "scripts/release-check.sh").read_text(encoding="utf-8")
    package_json = (REPO_ROOT / "package.json").read_text(encoding="utf-8")

    for command in [
        "npm test",
        "uv run alembic upgrade head",
        "npm run packages:typecheck",
        "npm run web:typecheck",
        "npm run api:openapi",
        "uv build",
    ]:
        assert command in script

    assert "docs/openapi.json" in script
    assert "Wheel must not include tests/" in script
    assert '"release:check": "sh scripts/release-check.sh"' in package_json


def test_alembic_migrations_apply_to_configured_database() -> None:
    database_url = os.environ.get("JIANDOU_TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("Set JIANDOU_TEST_DATABASE_URL to run migration integration checks.")
    if "test" not in database_url.lower():
        pytest.skip("JIANDOU_TEST_DATABASE_URL must point at a disposable test database.")

    env = os.environ.copy()
    env["JIANDOU_DATABASE_URL"] = database_url

    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )
    subprocess.run(
        ["uv", "run", "alembic", "check"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )


def test_ci_runs_release_facing_quality_gates() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    for expected in [
        "uv run ruff check backend tests migrations",
        "uv run pytest",
        "JIANDOU_TEST_DATABASE_URL",
        "uv run alembic upgrade head",
        "uv run jiandou openapi --output docs/openapi.json",
        "uv build",
        "npm run packages:typecheck",
        "npm run web:typecheck",
        "docker build -t jiandou:ci .",
    ]:
        assert expected in workflow


def test_repository_declares_open_source_maintenance_automation() -> None:
    dependabot = (REPO_ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
    codeowners = (REPO_ROOT / ".github/CODEOWNERS").read_text(encoding="utf-8")
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    for ecosystem in [
        'package-ecosystem: "github-actions"',
        'package-ecosystem: "npm"',
        'package-ecosystem: "pip"',
    ]:
        assert ecosystem in dependabot

    assert "interval: \"weekly\"" in dependabot
    assert "* @imi4u36d" in codeowners
    assert "/backend/" in codeowners
    assert "/frontends/" in codeowners
    assert "Dependabot opens weekly dependency update pull requests" in contributing


def test_repository_declares_support_channels() -> None:
    support = (REPO_ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    for expected in [
        "Usage Questions",
        "Bugs",
        "Feature Requests",
        "Security Issues",
        "SECURITY.md",
    ]:
        assert expected in support

    assert "SUPPORT.md" in readme


def _tracked_existing_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return [
        path
        for path in result.stdout.decode("utf-8").split("\0")
        if path and (REPO_ROOT / path).is_file()
    ]


def _is_forbidden_tracked_file(path: str) -> bool:
    if path in FORBIDDEN_TRACKED_FILES:
        return True
    if path.endswith(FORBIDDEN_TRACKED_SUFFIXES):
        return True
    return any(path.startswith(prefix) for prefix in FORBIDDEN_TRACKED_PREFIXES)
