from __future__ import annotations

from pathlib import Path
import sys


def _bootstrap_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    packages_root = repo_root / "packages"
    package_projects: list[Path] = []
    if packages_root.exists():
        package_projects = sorted(
            [
                child
                for child in packages_root.iterdir()
                if child.is_dir() and (child / "pyproject.toml").exists()
            ]
        )

    for candidate in [repo_root, *package_projects, packages_root]:
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


_bootstrap_path()

from backend_core.runtime import build_runtime


def main() -> None:
    runtime = build_runtime()
    runtime.service.recover_interrupted_tasks()
    runtime.worker.run_forever()


if __name__ == "__main__":
    main()
