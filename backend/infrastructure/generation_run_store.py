"""Generation run store — in-memory + local file persistence for generation runs.

from backend.shared import now_iso
Translates the Java LocalGenerationRunStore.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

from backend.config import settings


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _run_file_path(run_id: str) -> str:
    storage_root = getattr(settings, "storage_root", "./storage")
    run_dir = os.path.join(storage_root, "tasks", "_run_store")
    os.makedirs(run_dir, exist_ok=True)
    return os.path.join(run_dir, f"{run_id}.json")


class LocalGenerationRunStore:
    """In-memory + local file store for generation runs.

    Mirrors the Java LocalGenerationRunStore semantics:
    - All runs are kept in memory for fast access.
    - Each run is also persisted to a JSON file on disk under
      ``<storage_root>/tasks/_run_store/<run_id>.json`` so that runs survive restarts.
    - ``list_runs`` returns runs in reverse-chronological order (newest first).
    """

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def save(self, run_id: str, run: dict[str, Any]) -> None:
        """Save a run (upsert) to both memory and disk."""
        self._runs[run_id] = run
        self._persist(run_id, run)

    async def get(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve a run by ID. Checks memory first, then disk."""
        run = self._runs.get(run_id)
        if run is not None:
            return run
        return self._load_from_disk(run_id)

    async def list(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return up to *limit* runs, newest first."""
        all_ids = list(self._runs.keys())
        # Sort by updatedAt descending; fall back to id order
        sorted_ids = sorted(
            all_ids,
            key=lambda rid: self._runs[rid].get("updatedAt", ""),
            reverse=True,
        )
        return [self._runs[rid] for rid in sorted_ids[:limit]]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _persist(self, run_id: str, run: dict[str, Any]) -> None:
        try:
            file_path = _run_file_path(run_id)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(run, f, ensure_ascii=False, default=str)
        except OSError:
            pass  # non-fatal; in-memory copy still exists

    def _load_from_disk(self, run_id: str) -> dict[str, Any] | None:
        try:
            file_path = _run_file_path(run_id)
            if not os.path.isfile(file_path):
                return None
            with open(file_path, encoding="utf-8") as f:
                run: dict[str, Any] = json.load(f)
            self._runs[run_id] = run
            return run
        except (OSError, json.JSONDecodeError):
            return None
