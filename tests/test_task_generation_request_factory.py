from __future__ import annotations

from backend.domain.task_record import TaskRecord
from backend.services.task_generation_request_factory import TaskGenerationRequestFactory


class _Resolver:
    def supports_seed(self, model: str) -> bool:
        return True

    def value(self, section: str, key: str, fallback: str = "") -> str:
        return fallback


def test_image_request_factory_keeps_seed_auth_and_frame_metadata() -> None:
    factory = TaskGenerationRequestFactory(_Resolver())
    task = TaskRecord(
        id="task-1",
        owner_user_id=7,
        title="图片任务",
        request_snapshot={
            "textAnalysisModel": "text-model",
            "imageModel": "image-model",
            "seed": 42,
        },
    )

    request = factory.build_image_run_request(
        task,
        2,
        "frame prompt",
        1024,
        768,
        "reference.png",
        frame_role="last",
    )

    assert request["input"]["seed"] == 42
    assert request["input"]["frameRole"] == "last"
    assert request["metadata"] == {"relatedTaskId": "task-1", "clipIndex": 2, "frameRole": "last"}
    assert request["auth"] == {"userId": "7"}


def test_generated_image_seed_is_stable_for_task_and_clip() -> None:
    factory = TaskGenerationRequestFactory(_Resolver())
    task = TaskRecord(id="task-1", title="stable", request_snapshot={})

    assert factory.image_seed(task, 1) == factory.image_seed(task, 1)
    assert factory.image_seed(task, 1) != factory.image_seed(task, 2)
