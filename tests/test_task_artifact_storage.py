from __future__ import annotations

from types import SimpleNamespace

from backend.domain.task_record import TaskRecord
from backend.services.task_artifact_storage import TaskArtifactStorage


def test_storage_resolves_nested_last_frame_and_materializes_fallback_name() -> None:
    calls: list[tuple[str, str, str]] = []
    media = SimpleNamespace(
        materialize_artifact=lambda source, directory, name: calls.append(
            (source, directory, name)
        )
        or SimpleNamespace(public_url=f"/storage/{name}")
    )
    storage = TaskArtifactStorage(media)
    task = TaskRecord(id="task_1", title="Task", status="PENDING")

    artifact = storage.normalize(task, "https://example.test/frame.png", "", "keyframe")
    last_frame = storage.extract_last_frame_url(
        {"frames": [{"role": "last_frame", "image_url": {"url": "https://last.png"}}]}
    )

    assert artifact.public_url == "/storage/clip1-first.bin"
    assert calls == [
        (
            "https://example.test/frame.png",
            "tasks/task_1/running",
            "clip1-first.bin",
        )
    ]
    assert last_frame == "https://last.png"
