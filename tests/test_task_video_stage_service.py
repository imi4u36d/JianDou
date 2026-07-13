from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.services.task_video_clip_result_recorder import TaskVideoClipResultRecorder
from backend.services.task_video_stage_service import TaskVideoStageOptions, TaskVideoStageService
from backend.services.task_worker_status_stage_service import TaskWorkerExecutionContext, TaskWorkerStatusStageService

pytestmark = pytest.mark.service


@pytest.mark.asyncio
async def test_video_stage_generates_missing_clips_and_joins_ready_task(tmp_path: Path) -> None:
    repository = _RecordingRepository()
    generation_service = _RecordingGenerationService()
    media_service = _RecordingMediaService(tmp_path)
    task = _video_task()
    task.outputs.append(
        {
            "resultId": "result_clip_1",
            "resultType": "video",
            "clipIndex": 1,
            "downloadUrl": "/storage/tasks/task_video/running/clip1.mp4",
            "durationSeconds": 6,
            "extra": {"lastFrameUrl": "/storage/tasks/task_video/running/clip1-last.png"},
        }
    )
    service = _service(repository, generation_service, media_service)
    assert isinstance(service._clip_result_recorder, TaskVideoClipResultRecorder)

    result = await service.render_missing_videos(
        task,
        TaskWorkerExecutionContext("worker_1", "test", "manual"),
        TaskVideoStageOptions(poll_interval_seconds=0, max_polls=0, join_videos=True),
    )

    assert len(generation_service.requests) == 1
    request = generation_service.requests[0]
    assert request["metadata"]["clipIndex"] == 2
    assert request["input"]["firstFrameUrl"] == "https://oss.example.test/storage/tasks/task_video/running/clip1-last.png"
    assert request["input"]["lastFrameUrl"] == "https://oss.example.test/storage/tasks/task_video/running/clip2-last.png"

    assert result.video_run_ids == ["run_video_2"]
    assert result.latest_video_output_url == "/storage/tasks/task_video/joined/join-2.mp4"
    assert media_service.materialized == [
        ("https://provider.example.test/video-2.mp4", "tasks/task_video/running", "clip2.mp4"),
    ]
    assert media_service.concatenated == [
        (
            "tasks/task_video/joined",
            "join-2.mp4",
            ["/storage/tasks/task_video/running/clip1.mp4", "/storage/tasks/task_video/running/clip2.mp4"],
        )
    ]
    assert task.execution_context["clipVideoRunIds"] == ["run_video_2"]
    assert task.execution_context["latestJoinName"] == "join-2"
    assert task.execution_context["latestJoinOutputUrl"] == "/storage/tasks/task_video/joined/join-2.mp4"
    assert any(output["resultType"] == "video" and output["clipIndex"] == 2 for output in task.outputs)
    assert any(output["resultType"] == "video_join" for output in task.outputs)


@pytest.mark.asyncio
async def test_continue_task_creates_reusable_continue_attempt_and_completes(tmp_path: Path) -> None:
    repository = _RecordingRepository()
    generation_service = _RecordingGenerationService()
    media_service = _RecordingMediaService(tmp_path)
    task = _video_task(clip_count=1)
    repository.task = task
    service = _service(repository, generation_service, media_service)

    result = await service.continue_task(
        task.id,
        TaskWorkerExecutionContext("worker_2", "test", "manual"),
        TaskVideoStageOptions(poll_interval_seconds=0, max_polls=0, join_videos=False),
    )

    assert result.task_id == task.id
    assert result.video_run_ids == ["run_video_1"]
    assert task.status == "COMPLETED"
    assert task.progress == 100
    assert task.attempts[0]["triggerType"] == "continue"
    assert task.attempts[0]["status"] == "FINISHED"


def _video_task(clip_count: int = 2) -> TaskRecord:
    frame_contexts = []
    storyboard_clips = []
    for clip_index in range(1, clip_count + 1):
        start_url = (
            f"/storage/tasks/task_video/running/clip{clip_index}-first.png"
            if clip_index == 1
            else f"/storage/tasks/task_video/running/clip{clip_index - 1}-last.png"
        )
        frame_contexts.append(
            {
                "clipIndex": clip_index,
                "scene": f"scene {clip_index}",
                "targetDurationSeconds": 6,
                "startFrameUrl": start_url,
                "startFrameKeyframeUrl": f"/storage/tasks/task_video/running/clip{clip_index}-first.png",
                "endFrameConstraintUrl": f"/storage/tasks/task_video/running/clip{clip_index}-last.png",
            }
        )
        storyboard_clips.append(
            {
                "clipIndex": clip_index,
                "videoPrompt": f"video prompt {clip_index}",
                "targetDurationSeconds": 6,
                "minDurationSeconds": 6,
                "maxDurationSeconds": 6,
            }
        )
    return TaskRecord(
        id="task_video",
        owner_user_id=7,
        title="Video Task",
        status="COMPLETED",
        progress=100,
        task_type="video_generation",
        min_duration_seconds=6,
        max_duration_seconds=6,
        request_snapshot={
            "textAnalysisModel": "gpt-5.5",
            "imageModel": "gpt-image-2",
            "videoModel": "agnes-video-v2.0",
        },
        execution_context={
            "plannedClipCount": clip_count,
            "videoSize": "2560*1440",
            "clipFrameContexts": frame_contexts,
            "storyboardClips": storyboard_clips,
            "clipDurationPlan": [
                {
                    "clipIndex": clip_index,
                    "targetDurationSeconds": 6,
                    "minDurationSeconds": 6,
                    "maxDurationSeconds": 6,
                }
                for clip_index in range(1, clip_count + 1)
            ],
        },
    )


def _service(
    repository: _RecordingRepository,
    generation_service: _RecordingGenerationService,
    media_service: _RecordingMediaService,
) -> TaskVideoStageService:
    return TaskVideoStageService(
        task_repository=repository,
        execution_coordinator=TaskExecutionCoordinator(),
        generation_application_service=generation_service,
        runtime_support=TaskExecutionRuntimeSupport(local_media_artifact_service=media_service),
        artifact_assembler=TaskExecutionArtifactAssembler(media_service),
        status_stage_service=TaskWorkerStatusStageService(
            task_repository=repository,
            execution_coordinator=TaskExecutionCoordinator(),
        ),
        local_media_artifact_service=media_service,
    )


class _RecordingRepository:
    def __init__(self) -> None:
        self.task: TaskRecord | None = None
        self.saved_mutations: list[TaskPersistenceMutation] = []
        self.saved_tasks: list[TaskRecord] = []

    async def find_by_id(self, task_id: str) -> TaskRecord | None:
        return self.task if self.task and self.task.id == task_id else None

    async def save_mutation(self, mutation: TaskPersistenceMutation) -> None:
        self.saved_mutations.append(mutation)

    async def save(self, task: TaskRecord) -> None:
        self.saved_tasks.append(task)


class _RecordingGenerationService:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    async def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        clip_index = int(request["metadata"]["clipIndex"])
        output_url = f"https://provider.example.test/video-{clip_index}.mp4"
        return {
            "id": f"run_video_{clip_index}",
            "status": "completed",
            "updatedAt": "2026-01-01T00:00:06+00:00",
            "result": {
                "outputUrl": output_url,
                "mimeType": "video/mp4",
                "durationSeconds": request["input"]["durationSeconds"],
                "width": 2560,
                "height": 1440,
                "hasAudio": True,
                "metadata": {
                    "outputUrl": output_url,
                    "remoteSourceUrl": output_url,
                    "firstFrameUrl": request["input"]["firstFrameUrl"],
                    "requestedLastFrameUrl": request["input"].get("lastFrameUrl", ""),
                    "taskId": f"remote_task_{clip_index}",
                },
                "modelInfo": {
                    "provider": "agnes",
                    "providerModel": "agnes-video-v2.0",
                    "resolvedModel": "agnes-video-v2.0",
                },
            },
        }

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        return None


class _StoredArtifact:
    def __init__(self, public_url: str, absolute_path: str, file_name: str) -> None:
        self.public_url = public_url
        self.absolute_path = absolute_path
        self.file_name = file_name
        self.size_bytes = 0


class _RecordingMediaService:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.materialized: list[tuple[str, str, str]] = []
        self.concatenated: list[tuple[str, str, list[str]]] = []

    def publish_local_artifact(self, public_url: str, content_type: str = "", storage_key: str = "") -> str:  # noqa: ARG002
        return f"https://oss.example.test{public_url}"

    def materialize_artifact(self, source_url: str, relative_dir: str, target_file_name: str) -> _StoredArtifact:
        self.materialized.append((source_url, relative_dir, target_file_name))
        public_url = f"/storage/{relative_dir}/{target_file_name}"
        return _StoredArtifact(public_url, str(self.root / relative_dir / target_file_name), target_file_name)

    def concat_videos(self, relative_dir: str, output_file_name: str, segment_urls: list[str]) -> _StoredArtifact:
        self.concatenated.append((relative_dir, output_file_name, list(segment_urls)))
        public_url = f"/storage/{relative_dir}/{output_file_name}"
        return _StoredArtifact(public_url, str(self.root / relative_dir / output_file_name), output_file_name)

    def ensure_media_thumbnail(
        self,
        media_type: str,
        public_url: str,
        candidate_image_urls: list[str],
        max_width: int,
    ) -> str:  # noqa: ARG002
        return ""

    def resolve_absolute_path(self, file_url: str) -> str:
        return ""
