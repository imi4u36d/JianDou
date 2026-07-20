from __future__ import annotations

from sqlalchemy import event, select

from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository import TaskRepository
from backend.models.task import BizMaterialAsset, BizTaskModelCall
from backend.services.task_query_service import TaskQueryService


def _task(
    task_id: str,
    owner_user_id: int = 1,
    *,
    created_at: str = "2026-01-01T00:00:00+00:00",
    updated_at: str = "2026-01-01T00:01:00+00:00",
) -> TaskRecord:
    return TaskRecord(
        id=task_id,
        owner_user_id=owner_user_id,
        task_type="video_generation",
        title=f"Task {task_id}",
        status="PENDING",
        progress=10,
        created_at=created_at,
        updated_at=updated_at,
    )


async def test_task_list_sorting_separates_created_and_updated_times(db_session) -> None:
    repository = TaskRepository(db_session)
    old_but_updated = _task(
        "task_old_but_updated",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-03T00:00:00+00:00",
    )
    newly_created = _task(
        "task_newly_created",
        created_at="2026-01-02T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    await repository.save_mutation(TaskPersistenceMutation().set_task(old_but_updated))
    await repository.save_mutation(TaskPersistenceMutation().set_task(newly_created))

    service = TaskQueryService(repository)
    default_items = await service.list_tasks(1)
    updated_items = await service.list_tasks(1, sort="updated_desc")

    assert [item["id"] for item in default_items] == ["task_newly_created", "task_old_but_updated"]
    assert [item["id"] for item in updated_items] == ["task_old_but_updated", "task_newly_created"]


async def test_task_list_and_trace_use_lightweight_queries(db_session) -> None:
    repository = TaskRepository(db_session)
    task = _task("task_light_query")
    mutation = TaskPersistenceMutation().set_task(task)
    mutation.add_attempt(
        {
            "attemptId": "att_light_query",
            "attemptNo": 1,
            "triggerType": "create",
            "status": "QUEUED",
            "queueName": "default",
            "queueEnteredAt": "2026-01-01T00:00:00+00:00",
        }
    )
    mutation.add_trace(
        {
            "traceId": "trace_light_query",
            "timestamp": "2026-01-01T00:00:01+00:00",
            "stage": "dispatch",
            "event": "task.enqueued",
            "message": "queued",
            "payload": {"ok": True},
        }
    )
    mutation.add_model_call(
        {
            "modelCallId": "mdl_light_query",
            "callKind": "image",
            "stage": "rendering",
            "operation": "generation.image",
            "requestPayload": {"large": "x" * 1024},
            "responsePayload": {"large": "y" * 1024},
            "success": True,
        }
    )
    mutation.add_material(
        {
            "id": "asset_light_query",
            "ownerUserId": 1,
            "kind": "keyframe",
            "mediaType": "image",
            "fileUrl": "/storage/image.png",
            "metadata": {"large": "z" * 1024},
        }
    )
    await repository.save_mutation(mutation)

    statements: list[str] = []
    event.listen(
        db_session.bind.sync_engine,
        "before_cursor_execute",
        lambda _conn, _cursor, statement, _parameters, _context, _executemany: statements.append(statement),
    )

    service = TaskQueryService(repository)
    items = await service.list_tasks(1, sort="updated_desc")
    trace = await service.get_trace("task_light_query", 1, 10)

    assert [item["id"] for item in items] == ["task_light_query"]
    assert trace[0]["traceId"] == "trace_light_query"

    selected_sql = "\n".join(statement.lower() for statement in statements if statement.lstrip().lower().startswith("select"))
    assert "biz_task_model_calls" not in selected_sql
    assert "request_payload_json" not in selected_sql
    assert "response_payload_json" not in selected_sql
    assert "metadata_json" not in selected_sql


async def test_admin_overview_uses_constant_lightweight_queries(db_session) -> None:
    repository = TaskRepository(db_session)
    for index in range(12):
        task = _task(
            f"task_overview_{index:02d}",
            created_at=f"2026-01-{index + 1:02d}T00:00:00+00:00",
        )
        task.status = "FAILED" if index % 3 == 0 else "COMPLETED"
        await repository.save_mutation(TaskPersistenceMutation().set_task(task))

    statements: list[str] = []
    event.listen(
        db_session.bind.sync_engine,
        "before_cursor_execute",
        lambda _conn, _cursor, statement, _parameters, _context, _executemany: statements.append(statement),
    )

    overview = await TaskQueryService(repository).admin_overview()

    selected = [statement.lower() for statement in statements if statement.lstrip().lower().startswith("select")]
    assert len(selected) <= 8
    assert overview["counts"]["totalTasks"] == 12
    assert len(overview["recentTasks"]) == 8
    assert len(overview["recentFailures"]) == 4
    selected_sql = "\n".join(selected)
    assert "biz_task_model_calls" not in selected_sql
    assert "biz_material_assets" not in selected_sql
    assert "biz_task_results" not in selected_sql


async def test_task_detail_uses_lightweight_payload_and_filters_inline_media(db_session) -> None:
    repository = TaskRepository(db_session)
    inline_image = "data:image/png;base64," + ("a" * 8192)
    task = _task("task_detail_light")
    task.creative_prompt = "p" * 4096
    task.request_snapshot = {
        "taskType": "image_generation",
        "creativePrompt": "r" * 4096,
        "transcriptText": "t" * 4096,
        "referenceImageUrls": [inline_image, "/storage/reference.png"],
    }
    task.execution_context = {
        "clipPrompts": ["x" * 8192],
        "analysisScriptText": "s" * 8192,
        "referenceImageUrls": [inline_image],
    }
    mutation = TaskPersistenceMutation().set_task(task)
    mutation.add_attempt(
        {
            "attemptId": "att_detail_light",
            "attemptNo": 1,
            "triggerType": "create",
            "status": "RUNNING",
            "resumeFromStage": "render",
            "payload": {"large": "a" * 8192},
        }
    )
    mutation.add_status_history(
        {
            "id": "status_detail_light",
            "previousStatus": "PENDING",
            "currentStatus": "RENDERING",
            "payload": {"large": "b" * 8192},
        }
    )
    mutation.add_model_call(
        {
            "modelCallId": "mdl_detail_light",
            "callKind": "image",
            "stage": "rendering",
            "operation": "generation.image",
            "requestPayload": {"large": "c" * 8192},
            "responsePayload": {"large": "d" * 8192},
            "success": True,
        }
    )
    mutation.add_material(
        {
            "id": "asset_detail_light",
            "ownerUserId": 1,
            "kind": "output",
            "mediaType": "image",
            "fileUrl": inline_image,
            "thumbnailUrl": "/storage/thumbs/detail-light.jpg",
            "metadata": {"large": "e" * 8192},
        }
    )
    mutation.add_result(
        {
            "id": "result_detail_light",
            "resultType": "image",
            "clipIndex": 1,
            "title": "Generated",
            "reason": "done",
            "previewUrl": inline_image,
            "downloadUrl": "/storage/detail-light.png",
        }
    )
    await repository.save_mutation(mutation)

    statements: list[str] = []
    event.listen(
        db_session.bind.sync_engine,
        "before_cursor_execute",
        lambda _conn, _cursor, statement, _parameters, _context, _executemany: statements.append(statement),
    )

    detail = await repository.find_detail_light("task_detail_light", 1)

    assert detail is not None
    assert detail["creativePrompt"] == "p" * 2000
    assert detail["requestSnapshot"]["creativePrompt"] == "r" * 2000
    assert detail["requestSnapshot"]["transcriptText"] == "t" * 2000
    assert detail["requestSnapshot"]["referenceImageUrls"] == ["/storage/reference.png"]
    assert detail["executionContext"] == {}
    assert detail["storyboardScript"] == ""
    assert detail["attempts"][0]["payload"] == {}
    assert detail["modelCalls"] == []
    assert detail["materials"][0]["fileUrl"] == ""
    assert detail["materials"][0]["thumbnailUrl"] == "/storage/thumbs/detail-light.jpg"
    assert detail["outputs"][0]["previewPath"] == ""
    assert detail["outputs"][0]["downloadPath"] == "/storage/detail-light.png"

    selected_sql = "\n".join(statement.lower() for statement in statements if statement.lstrip().lower().startswith("select"))
    normalized_sql = selected_sql.replace("`", "")
    assert "biz_tasks.context_json" not in normalized_sql
    assert "biz_task_attempts.payload_json" not in normalized_sql
    assert "biz_task_stage_runs.input_summary_json" not in normalized_sql
    assert "biz_task_stage_runs.output_summary_json" not in normalized_sql
    assert "biz_tasks.request_payload_json" in normalized_sql
    assert "biz_task_model_calls.response_payload_json" not in normalized_sql
    assert "biz_material_assets.metadata_json" not in normalized_sql


async def test_model_call_and_material_payloads_are_sanitized_before_persisting(db_session) -> None:
    repository = TaskRepository(db_session)
    huge_b64 = "a" * 4096
    task = _task("task_payload_sanitized")
    mutation = TaskPersistenceMutation().set_task(task)
    mutation.add_model_call(
        {
            "modelCallId": "mdl_payload_sanitized",
            "callKind": "image",
            "stage": "rendering",
            "operation": "generation.image",
            "requestPayload": {"image": {"b64_json": huge_b64}},
            "responsePayload": {"data": [{"b64_json": huge_b64}]},
            "success": True,
        }
    )
    mutation.add_material(
        {
            "id": "asset_payload_sanitized",
            "ownerUserId": 1,
            "kind": "keyframe",
            "mediaType": "image",
            "fileUrl": "/storage/image.png",
            "metadata": {"sourceMetadata": {"providerResponse": {"data": [{"b64_json": huge_b64}]}}},
        }
    )

    await repository.save_mutation(mutation)

    model_call = (
        await db_session.execute(
            select(BizTaskModelCall).where(BizTaskModelCall.task_model_call_id == "mdl_payload_sanitized")
        )
    ).scalar_one()
    material = (
        await db_session.execute(
            select(BizMaterialAsset).where(BizMaterialAsset.material_asset_id == "asset_payload_sanitized")
        )
    ).scalar_one()

    persisted = "\n".join(
        [
            model_call.request_payload_json,
            model_call.response_payload_json,
            material.metadata_json,
        ]
    )
    assert "b64_json" not in persisted
    assert huge_b64 not in persisted
    assert "base64ImageRedacted" in persisted
