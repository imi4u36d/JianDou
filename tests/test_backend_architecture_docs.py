from __future__ import annotations

import pytest
pytestmark = pytest.mark.infra
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_DOC = REPO_ROOT / "docs/backend-architecture.md"
DOCUMENTED_BACKEND_PATHS = [
    "backend/routers",
    "backend/schemas",
    "backend/services",
    "backend/domain",
    "backend/infrastructure",
    "backend/models",
    "backend/auth.py",
    "backend/config.py",
    "backend/__main__.py",
]


def test_backend_architecture_doc_covers_existing_top_level_modules() -> None:
    text = ARCHITECTURE_DOC.read_text(encoding="utf-8")

    for documented_path in DOCUMENTED_BACKEND_PATHS:
        assert (REPO_ROOT / documented_path).exists()
        assert documented_path in text


def test_contributor_docs_link_backend_architecture() -> None:
    for filename in ["README.md", "CONTRIBUTING.md"]:
        text = (REPO_ROOT / filename).read_text(encoding="utf-8")
        assert "docs/backend-architecture.md" in text
