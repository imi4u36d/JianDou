from __future__ import annotations

from typing import Any

import pytest

from backend.domain.enums import TaskStatus
from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.services.task_worker_service import TaskWorkerPipelineHandler
from backend.services.task_worker_status_stage_service import TaskWorkerExecutionContext

pytestmark = pytest.mark.service


@pytest.mark.asyncio
async def test_workspace_image_task_generates_each_requested_output() -> None:
    repository = _RecordingRepository()
    generation_service = _RecordingGenerationService()
    media_service = _PublishingMediaService()
    coordinator = TaskExecutionCoordinator()
    handler = TaskWorkerPipelineHandler(
        task_repository=repository,
        execution_coordinator=coordinator,
        generation_application_service=generation_service,
        runtime_support=TaskExecutionRuntimeSupport(local_media_artifact_service=media_service),
        artifact_assembler=TaskExecutionArtifactAssembler(media_service),
    )
    task = TaskRecord(
        id="task_workspace",
        owner_user_id=12,
        title="Workspace Image",
        task_type="image_generation",
        status=TaskStatus.PENDING.value,
        aspect_ratio="1:1",
        creative_prompt="A clean product render",
        request_snapshot={
            "textAnalysisModel": "gpt-5.5",
            "imageModel": "gpt-image-2",
            "creativePrompt": "A clean product render",
            "imageSize": "2048x2048",
            "outputCount": {"auto": False, "count": 3},
        },
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )

    await handler._process_workspace_image_task(
        task,
        TaskWorkerExecutionContext("worker_1", "test_worker", "queue"),
        [2048, 2048],
    )

    assert len(generation_service.requests) == 3
    assert [request["input"]["width"] for request in generation_service.requests] == [2048, 2048, 2048]
    assert [request["storage"]["fileStem"] for request in generation_service.requests] == [
        "workspace-image",
        "workspace-image-2",
        "workspace-image-3",
    ]
    assert len(task.materials) == 3
    assert len(task.outputs) == 3
    assert [item["fileUrl"] for item in task.materials] == [
        "https://oss.example.test/tasks/task_workspace/running/workspace-image-task_workspace.png",
        "https://oss.example.test/tasks/task_workspace/running/workspace-image-task_workspace-2.png",
        "https://oss.example.test/tasks/task_workspace/running/workspace-image-task_workspace-3.png",
    ]
    assert [item["clipIndex"] for item in task.outputs] == [1, 2, 3]
    assert task.completed_output_count == 3
    assert task.status == TaskStatus.COMPLETED.value
    assert task.execution_context["latestImageOutputUrls"] == [
        "https://oss.example.test/tasks/task_workspace/running/workspace-image-task_workspace.png",
        "https://oss.example.test/tasks/task_workspace/running/workspace-image-task_workspace-2.png",
        "https://oss.example.test/tasks/task_workspace/running/workspace-image-task_workspace-3.png",
    ]
    assert repository.saved_tasks[-1] is task


@pytest.mark.asyncio
async def test_workspace_image_task_records_actual_size_when_request_is_auto() -> None:
    repository = _RecordingRepository()
    generation_service = _RecordingGenerationService()
    media_service = _PublishingMediaService()
    coordinator = TaskExecutionCoordinator()
    handler = TaskWorkerPipelineHandler(
        task_repository=repository,
        execution_coordinator=coordinator,
        generation_application_service=generation_service,
        runtime_support=TaskExecutionRuntimeSupport(local_media_artifact_service=media_service),
        artifact_assembler=TaskExecutionArtifactAssembler(media_service),
    )
    task = TaskRecord(
        id="task_workspace_auto",
        owner_user_id=12,
        title="Workspace Image",
        task_type="image_generation",
        status=TaskStatus.PENDING.value,
        aspect_ratio="9:16",
        creative_prompt="A clean product render",
        request_snapshot={
            "textAnalysisModel": "gpt-5.5",
            "imageModel": "gpt-image-2",
            "creativePrompt": "A clean product render",
            "outputCount": {"auto": False, "count": 1},
        },
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )

    await handler._process_workspace_image_task(
        task,
        TaskWorkerExecutionContext("worker_1", "test_worker", "queue"),
        [0, 0],
    )

    assert generation_service.requests[0]["input"]["width"] == 0
    assert generation_service.requests[0]["input"]["height"] == 0
    assert "画面比例：9:16" in generation_service.requests[0]["input"]["prompt"]
    assert "2160x3840" in generation_service.requests[0]["input"]["prompt"]
    assert task.execution_context["imageSize"] == "864x1821"
    assert task.execution_context["actualImageSize"] == "864x1821"


class _RecordingRepository:
    def __init__(self) -> None:
        self.saved_mutations: list[TaskPersistenceMutation] = []
        self.saved_tasks: list[TaskRecord] = []

    async def save_mutation(self, mutation: TaskPersistenceMutation) -> None:
        self.saved_mutations.append(mutation)

    async def save(self, task: TaskRecord) -> None:
        self.saved_tasks.append(task)

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"Unexpected repository call: {name}")


class _RecordingGenerationService:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    async def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        index = len(self.requests)
        output_url = f"https://provider.example.test/image-{index}.png"
        width = request["input"]["width"] or 864
        height = request["input"]["height"] or 1821
        return {
            "id": f"run_image_{index}",
            "updatedAt": "2026-01-01T00:00:01+00:00",
            "result": {
                "outputUrl": output_url,
                "mimeType": "image/png",
                "width": width,
                "height": height,
                "metadata": {
                    "outputUrl": output_url,
                    "fileUrl": output_url,
                    "remoteSourceUrl": output_url,
                },
                "modelInfo": {
                    "provider": "openai",
                    "providerModel": "gpt-image-2",
                    "resolvedModel": "gpt-image-2",
                },
            },
        }


class _StoredArtifact:
    def __init__(self, public_url: str) -> None:
        self.public_url = public_url


class _PublishingMediaService:
    def materialize_artifact(self, source_url: str, relative_dir: str, target_file_name: str) -> _StoredArtifact:
        return _StoredArtifact(f"https://oss.example.test/{relative_dir}/{target_file_name}")

    def ensure_media_thumbnail(
        self,
        media_type: str,
        public_url: str,
        candidate_image_urls: list[str],
        max_width: int,
    ) -> str:
        return public_url

    def resolve_absolute_path(self, file_url: str) -> str:
        return ""
