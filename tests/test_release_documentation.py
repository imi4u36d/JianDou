from __future__ import annotations

import pytest

pytestmark = pytest.mark.infra
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_changelog_has_unreleased_section_and_current_version() -> None:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## [Unreleased]" in changelog
    assert "## [0.1.0] - 2026-06-19" in changelog
    assert "Keep a Changelog" in changelog
    assert "Semantic Versioning" in changelog


def test_release_process_documents_required_gates() -> None:
    release_process = (REPO_ROOT / "docs/release-process.md").read_text(encoding="utf-8")

    for expected in [
        "npm run release:check",
        "docker build -t jiandou:release-check .",
        "CHANGELOG.md",
        "pyproject.toml",
        "package.json",
    ]:
        assert expected in release_process


def test_release_docs_are_linked_from_contributor_surfaces() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    pr_template = (REPO_ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")

    assert "CHANGELOG.md" in readme
    assert "docs/release-process.md" in readme
    assert "CHANGELOG.md" in contributing
    assert "docs/release-process.md" in contributing
    assert "CHANGELOG.md" in pr_template
