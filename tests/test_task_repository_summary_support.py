from __future__ import annotations

from sqlalchemy import select

from backend.infrastructure.task_repository_summary_support import TaskRepositorySummarySupport
from backend.models.task import BizTask


def test_summary_filter_policy_normalizes_status_and_task_type_lists() -> None:
    support = TaskRepositorySummarySupport()
    statement = support._apply_task_summary_filters(
        select(BizTask),
        owner_user_id=7,
        q=" cat ",
        status="active",
        task_type="image_generation, image_to_image",
        exclude_task_type="video_generation",
    )
    sql = str(statement)

    assert support._task_type_values(" image, video ,, ") == ["image", "video"]
    assert "biz_tasks.owner_user_id" in sql
    assert "biz_tasks.status IN" in sql
    assert "biz_tasks.task_type IN" in sql
    assert "biz_tasks.task_type NOT IN" in sql


def test_summary_sort_policy_defaults_to_stable_created_order() -> None:
    support = TaskRepositorySummarySupport()
    sql = str(support._apply_task_summary_sort(select(BizTask), None))

    assert "ORDER BY biz_tasks.create_time DESC, biz_tasks.id DESC" in sql
