from __future__ import annotations

from pathlib import Path
import sys


def _bootstrap_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    packages_root = repo_root / "packages"
    for candidate in (repo_root, packages_root):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


_bootstrap_path()

from backend_core.runtime import build_runtime


def main() -> None:
    runtime = build_runtime()
    runtime.worker.run_forever()


if __name__ == "__main__":
    main()
