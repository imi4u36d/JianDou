from types import SimpleNamespace

from backend.domain.task_record import TaskRecord
from backend.services.task_render_reference_selector import (
    existing_character_sheet_urls,
    frame_reference_image_urls,
    matching_character_indexes,
)


def test_reference_selector_orders_named_characters_and_respects_provider_limit() -> None:
    characters = [SimpleNamespace(name="Alice"), SimpleNamespace(name="Bob"), SimpleNamespace(name="Carol")]

    references = frame_reference_image_urls(
        "Bob meets Alice before Carol",
        "/storage/scene.png",
        ["/storage/alice.png", "/storage/bob.png", "/storage/carol.png"],
        characters,
    )

    assert matching_character_indexes("Bob meets Alice", characters, 3) == [2, 1]
    assert references == ["/storage/scene.png", "/storage/bob.png", "/storage/alice.png"]


def test_reference_selector_reads_only_materialized_character_sheets() -> None:
    task = TaskRecord(id="task-1", owner_user_id=7, title="Task")
    task.materials.extend([
        {
            "kind": "character_sheet",
            "clipIndex": 1001,
            "fileUrl": "/storage/character-1.png",
            "metadata": {},
        },
        {
            "kind": "character_sheet",
            "fileUrl": "https://provider.test/character-2.png",
            "metadata": {"characterIndex": 2},
        },
        {"kind": "keyframe-first", "clipIndex": 1, "fileUrl": "/storage/frame.png"},
    ])

    assert existing_character_sheet_urls(task) == {1: "/storage/character-1.png"}
