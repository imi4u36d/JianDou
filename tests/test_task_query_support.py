from unittest.mock import AsyncMock

from backend.domain.task_record import TaskRecord
from backend.services.task_query_cache import TaskQueryCache
from backend.services.task_query_policy import matches_task_status, task_comparator, task_type_set


def _task(task_id: str, status: str, created_at: str, progress: int = 0) -> TaskRecord:
    return TaskRecord(
        id=task_id,
        owner_user_id=7,
        title=task_id,
        status=status,
        progress=progress,
        created_at=created_at,
        updated_at=created_at,
    )


def test_task_query_policy_normalizes_types_status_and_stable_sort() -> None:
    older = _task("older", "PENDING", "2026-01-01T00:00:00Z")
    newer = _task("newer", "RENDERING", "2026-01-02T00:00:00Z")
    newer.is_queued = True

    assert task_type_set(" image_generation, video_generation ,, ") == {
        "image_generation",
        "video_generation",
    }
    assert matches_task_status(newer, "active") is True
    assert matches_task_status(newer, "queued") is True
    assert sorted([older, newer], key=task_comparator("created_desc")) == [newer, older]


async def test_task_query_cache_owns_normalized_keys_and_invalidation_prefix() -> None:
    backend = AsyncMock()
    cache = TaskQueryCache(backend)

    key = cache.task_list_key(7, " Cat ", " ACTIVE ", " Created_Desc ", None, None, 10, 20)
    await cache.invalidate_task_lists(7)

    assert key == "task:list:7:cat:active:created_desc:::10:20"
    backend.delete_prefix.assert_awaited_once_with("task:list:7:")
