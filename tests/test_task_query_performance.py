from __future__ import annotations

from sqlalchemy import event, select

from backend.domain.task_record import TaskRecord
from backend.infrastructure.task_persistence_mutation import TaskPersistenceMutation
from backend.infrastructure.task_repository import TaskRepository
from backend.models.task import BizMaterialAsset, BizTaskModelCall
from backend.services.task_query_service import TaskQueryService


def _task(task_id: str, owner_user_id: int = 1) -> TaskRecord:
    return TaskRecord(
        id=task_id,
        owner_user_id=owner_user_id,
        task_type="video_generation",
        title=f"Task {task_id}",
        status="PENDING",
        progress=10,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:01:00+00:00",
    )


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
    assert "biz_material_assets" not in selected_sql
    assert "request_payload_json" not in selected_sql
    assert "response_payload_json" not in selected_sql
    assert "metadata_json" not in selected_sql


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
