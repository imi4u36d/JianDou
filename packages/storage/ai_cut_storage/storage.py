from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import shutil

from ai_cut_shared.config import Settings
from ai_cut_shared.utils import new_id, safe_filename


@dataclass(frozen=True)
class StoredFile:
    asset_id: str
    original_file_name: str
    stored_file_name: str
    relative_path: str
    absolute_path: Path
    public_url: str
    size_bytes: int
    sha256: str


class MediaStorage:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.storage_root
        self.uploads_root = settings.uploads_root
        self.outputs_root = settings.outputs_root
        self.temp_root = settings.temp_root
        self.ensure_directories()

    def ensure_directories(self) -> None:
        for directory in (self.root, self.uploads_root, self.outputs_root, self.temp_root):
            directory.mkdir(parents=True, exist_ok=True)

    def _relative(self, absolute_path: Path) -> str:
        return absolute_path.resolve().relative_to(self.root.resolve()).as_posix()

    def build_public_url(self, relative_path: str | Path) -> str:
        rel = Path(relative_path).as_posix()
        return f"{self.settings.storage.public_base_url.rstrip('/')}/{rel.lstrip('/')}"

    def save_upload(self, file_obj, original_name: str, mime_type: str | None = None) -> StoredFile:
        asset_id = new_id("asset")
        safe_name = safe_filename(original_name)
        stored_name = f"{asset_id}_{safe_name}"
        absolute_path = self.uploads_root / stored_name
        sha256 = hashlib.sha256()
        size_bytes = 0

        with absolute_path.open("wb") as handle:
            while True:
                chunk = file_obj.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                sha256.update(chunk)
                size_bytes += len(chunk)

        if hasattr(file_obj, "seek"):
            try:
                file_obj.seek(0)
            except Exception:
                pass

        relative_path = self._relative(absolute_path)
        return StoredFile(
            asset_id=asset_id,
            original_file_name=original_name,
            stored_file_name=stored_name,
            relative_path=relative_path,
            absolute_path=absolute_path,
            public_url=self.build_public_url(relative_path),
            size_bytes=size_bytes,
            sha256=sha256.hexdigest(),
        )

    def task_work_dir(self, task_id: str) -> Path:
        work_dir = self.temp_root / task_id
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir

    def task_output_path(self, task_id: str, clip_index: int) -> Path:
        output_dir = self.outputs_root / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{clip_index:02d}.mp4"

    def task_context_path(self, task_id: str) -> Path:
        context_dir = self.temp_root / "task_context"
        context_dir.mkdir(parents=True, exist_ok=True)
        return context_dir / f"{task_id}.json"

    def task_trace_path(self, task_id: str) -> Path:
        trace_dir = self.temp_root / "task_trace"
        trace_dir.mkdir(parents=True, exist_ok=True)
        return trace_dir / f"{task_id}.jsonl"

    def save_task_context(self, task_id: str, payload: dict[str, object]) -> None:
        path = self.task_context_path(task_id)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_task_context(self, task_id: str) -> dict[str, object]:
        path = self.task_context_path(task_id)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def delete_path(self, path: str | Path) -> None:
        absolute = Path(path)
        if not absolute.is_absolute():
            absolute = (self.root / absolute).resolve()
        if absolute.exists():
            absolute.unlink()

    def remove_output_bundle(self, task_id: str) -> None:
        output_dir = self.outputs_root / task_id
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)
        work_dir = self.temp_root / task_id
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)

    def remove_task_artifacts(self, task_id: str) -> None:
        self.remove_output_bundle(task_id)
        for path in (self.task_context_path(task_id), self.task_trace_path(task_id)):
            if path.exists():
                path.unlink(missing_ok=True)
