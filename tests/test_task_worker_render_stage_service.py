from __future__ import annotations

from typing import Any

import pytest

from backend.domain.enums import TaskStatus
from backend.domain.task_record import TaskRecord
from backend.domain.task_storyboard_planner import CharacterDefinition
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.services.stubs import TaskStoryboardPlannerStub
from backend.services.task_artifact_assembler import TaskExecutionArtifactAssembler
from backend.services.task_execution_coordinator import TaskExecutionCoordinator
from backend.services.task_execution_runtime_support import TaskExecutionRuntimeSupport
from backend.services.task_render_stage_payloads import RenderStageRequest
from backend.services.task_worker_render_stage_service import TaskWorkerRenderStageService
from backend.services.task_worker_status_stage_service import TaskWorkerExecutionContext, TaskWorkerStatusStageService

pytestmark = pytest.mark.service


@pytest.mark.asyncio
async def test_render_generates_character_sheet_before_keyframes_and_references_it() -> None:
    repository = _RecordingRepository()
    generation_service = _RecordingGenerationService()
    media_service = _PublishingMediaService()
    task = TaskRecord(
        id="task_character_sheet_video",
        owner_user_id=7,
        title="角色视频",
        status=TaskStatus.PLANNING.value,
        progress=35,
        active_attempt_id="attempt_1",
        attempts=[{"attemptId": "attempt_1", "status": "RUNNING"}],
        task_type="video_generation",
        aspect_ratio="16:9",
        request_snapshot={
            "textAnalysisModel": "gpt-5.5",
            "imageModel": "gpt-image-2",
            "videoModel": "agnes-video-v2.0",
            "seed": 42,
        },
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    shot = TaskStoryboardPlannerStub.StoryboardShotPlan(
        sequential_index=1,
        shot_label="1",
        scene="社区门口",
        video_prompt="阿姨打开药箱",
        first_frame_prompt="阿姨站在药箱旁",
        last_frame_prompt="阿姨递出药品",
    )
    service = TaskWorkerRenderStageService(
        task_repository=repository,
        execution_coordinator=TaskExecutionCoordinator(),
        generation_application_service=generation_service,
        runtime_support=TaskExecutionRuntimeSupport(local_media_artifact_service=media_service),
        artifact_assembler=TaskExecutionArtifactAssembler(media_service),
        status_stage_service=TaskWorkerStatusStageService(execution_coordinator=TaskExecutionCoordinator()),
    )

    await service.render(
        task,
        TaskWorkerExecutionContext("worker_1", "test", "queue"),
        RenderStageRequest(
            shot_plans=[shot],
            clip_duration_plan=[[5, 5, 5]],
            width=2560,
            height=1440,
            duration_seconds=5,
            video_size="2560*1440",
            character_definitions=[
                CharacterDefinition("李阿姨", "灰发、蓝色雨衣、红色围巾", "社区志愿者，灰发、蓝色雨衣、红色围巾"),
            ],
        ),
    )

    assert [request["kind"] for request in generation_service.requests] == ["image", "image", "image"]
    assert generation_service.requests[0]["metadata"]["variantKind"] == "character_sheet"
    assert generation_service.requests[0]["input"]["frameRole"] == "sheet"

    sheet_reference_uri = "data:image/png;base64,character1-sheet.png"
    first_frame_reference_uri = "data:image/png;base64,clip1-first.png"
    first_keyframe_request = generation_service.requests[1]
    last_keyframe_request = generation_service.requests[2]
    assert first_keyframe_request["input"]["frameRole"] == "first"
    assert first_keyframe_request["input"]["referenceImageUrls"] == [sheet_reference_uri]
    assert last_keyframe_request["input"]["frameRole"] == "last"
    assert first_frame_reference_uri in last_keyframe_request["input"]["referenceImageUrls"]
    assert sheet_reference_uri in last_keyframe_request["input"]["referenceImageUrls"]

    assert any(material["kind"] == "character_sheet" for material in task.materials)
    assert task.execution_context["characterSheetUrls"] == [
        "/storage/tasks/task_character_sheet_video/running/character1-sheet.png"
    ]
    assert any(row["stageName"] == "planning" and row["clipIndex"] == 1001 for row in task.stage_runs)


def test_frame_reference_selection_limits_multi_character_payload() -> None:
    service = TaskWorkerRenderStageService(
        generation_application_service=_RecordingGenerationService(),
        runtime_support=TaskExecutionRuntimeSupport(local_media_artifact_service=_PublishingMediaService()),
    )

    references = service._frame_reference_image_urls(
        "尾帧目标：小周把药递给志愿者甲，李奶奶在旁边点头。",
        "/storage/tasks/task_1/running/clip1-first.png",
        [
            "/storage/tasks/task_1/running/character1-sheet.png",
            "/storage/tasks/task_1/running/character2-sheet.png",
            "/storage/tasks/task_1/running/character3-sheet.png",
            "/storage/tasks/task_1/running/character4-sheet.png",
        ],
        [
            CharacterDefinition("李奶奶", "银发", "老人"),
            CharacterDefinition("小周", "黑色雨衣", "年轻人"),
            CharacterDefinition("志愿者甲", "蓝色马甲", "志愿者"),
            CharacterDefinition("志愿者乙", "绿色马甲", "志愿者"),
        ],
    )

    assert references == [
        "/storage/tasks/task_1/running/clip1-first.png",
        "/storage/tasks/task_1/running/character2-sheet.png",
        "/storage/tasks/task_1/running/character3-sheet.png",
    ]


class _RecordingRepository:
    def __init__(self) -> None:
        self.saved_mutations: list[TaskPersistenceMutation] = []
        self.saved_tasks: list[TaskRecord] = []

    async def save_mutation(self, mutation: TaskPersistenceMutation) -> None:
        self.saved_mutations.append(mutation)

    async def save(self, task: TaskRecord) -> None:
        self.saved_tasks.append(task)


class _RecordingGenerationService:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    async def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        index = len(self.requests)
        if request["kind"] == "video":
            output_url = "https://provider.example.test/video-1.mp4"
            return {
                "id": "run_video_1",
                "status": "completed",
                "updatedAt": "2026-01-01T00:00:04+00:00",
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
                    },
                    "modelInfo": {
                        "provider": "agnes",
                        "providerModel": "agnes-video-v2.0",
                        "resolvedModel": "agnes-video-v2.0",
                    },
                },
            }
        output_url = f"https://provider.example.test/image-{index}.png"
        return {
            "id": f"run_image_{index}",
            "updatedAt": "2026-01-01T00:00:01+00:00",
            "result": {
                "outputUrl": output_url,
                "mimeType": "image/png",
                "width": request["input"]["width"],
                "height": request["input"]["height"],
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
        return _StoredArtifact(f"/storage/{relative_dir}/{target_file_name}")

    def image_data_uri_from_public_url(self, public_url: str) -> str:
        if not public_url.startswith("/storage/"):
            return ""
        return f"data:image/png;base64,{public_url.rsplit('/', 1)[-1]}"

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
