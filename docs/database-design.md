# Database Design Notes

This document records the current backend schema contract and the cleanup path. The schema still contains legacy fields from rapid product iteration, so new changes should follow the direction below instead of copying old patterns.

## Current Problems

- Status values are stored as free-form strings in many tables.
- Timestamps are stored as `String(32)` ISO text instead of typed datetime columns.
- Boolean flags such as `is_deleted`, `success`, `selected`, and `has_audio` are stored as integers.
- Several task fields duplicate data now held in request snapshots or material/result tables.
- JSON text columns are used for both immutable request snapshots and mutable runtime state without clear naming.
- Most tables have no comments, no documented ownership boundary, and limited indexes.

## Naming Rules

- Public identifiers use `{domain}_id`, for example `task_id`, `workflow_id`, and `material_asset_id`.
- Internal numeric primary keys remain named `id`.
- New timestamps should use `created_at` and `updated_at`. Existing `create_time` and `update_time` are legacy names kept for compatibility.
- JSON text columns should end in `_json`.
- Soft delete columns should be named `is_deleted` until the migration to typed boolean columns.

## Status Fields

Do not introduce new ad hoc status strings. Use enums from `backend/domain/enums.py`:

- `TaskStatus` for `biz_tasks.status`
- `AttemptStatus` for `biz_task_attempts.status`
- `AttemptTriggerType` for `biz_task_attempts.trigger_type`
- `StageRunStatus` for `biz_task_stage_runs.status`
- `WorkerStatus` for `biz_worker_instances.status`
- `QueueEventType` for `biz_task_queue_events.event_type`
- `UserRole` for `sys_user.role`
- `UserStatus` for `sys_user.status`
- `InviteStatus` for `sys_invite_code.status`
- `WorkflowStatus` for `biz_stage_workflows.status`
- `WorkflowStage` for `biz_stage_workflows.current_stage` and `biz_stage_versions.stage_type`
- `WorkflowDurationMode` for `biz_stage_workflows.duration_mode`
- `StageVersionStatus` for `biz_stage_versions.status`

Current database-level constraints:

- `sys_user.role` is constrained to `USER` or `ADMIN`.
- `sys_user.status` is constrained to `ACTIVE` or `DISABLED`.
- `sys_user.task_concurrency_limit` is constrained to the supported range `1..20`.
- `sys_invite_code.role` is constrained to `USER` or `ADMIN`.
- `sys_invite_code.status` is constrained to `UNUSED`, `USED`, `EXPIRED`, or `REVOKED`.
- `sys_credit_transaction.transaction_type` is constrained to `CONSUME`, `USAGE`, `REFUND`, or `ADJUST`.
- `biz_stage_workflows.status`, `current_stage`, and `duration_mode` are constrained to workflow enum values.
- `biz_stage_workflows.effect_rating` and `biz_stage_versions.rating` are constrained to `1..5` when present.
- `biz_stage_versions.stage_type` and `status` are constrained to workflow stage/version enum values.
- `biz_task_attempts.trigger_type` and `status` are constrained to task execution enum values. `PENDING` is temporarily accepted for legacy queue compatibility.
- `biz_task_stage_runs.status` is constrained to stage run enum values.
- `biz_task_queue_events.event_type` is constrained to queue event enum values.
- `biz_worker_instances.status` is constrained to worker status enum values.
- `biz_tasks.status` is constrained to `TaskStatus` values.
- `biz_tasks.progress`, `effect_rating`, retry count, duration range, and soft delete flag are constrained to valid ranges.
- `biz_task_status_history.progress` and soft delete flag are constrained, while empty status values remain allowed for trace-only rows.
- `biz_task_model_calls.success`, status code fields, latency/duration, token counts, and soft delete flag are constrained to valid ranges.
- `biz_task_results` media timing, dimensions, file size, clip index, and soft delete flag are constrained to non-negative/valid ranges.
- `biz_material_assets` selection/audio flags, ratings, clip/version numbers, media dimensions, size, duration, and soft delete flag are constrained to valid ranges.

Provider/model statuses should not be stored in `biz_task_stage_runs.status`; keep them in `biz_task_model_calls.status` or stage output summary JSON.

## Core Task Tables

`biz_tasks` is the aggregate root for a user-created generation task. It should contain lifecycle, ownership, high-level request metadata, and pointers to normalized child rows.

Fields to keep:

- `task_id`
- `owner_user_id`
- `task_type`
- `title`
- `aspect_ratio`
- `min_duration_seconds`
- `max_duration_seconds`
- `request_payload_json`
- `context_json`
- `creative_prompt`
- `task_seed`
- `status`
- `progress`
- `error_code`
- `error_message`
- `retry_count`
- `started_at`
- `finished_at`
- `create_time`
- `update_time`
- `is_deleted`

Fields considered legacy or duplicated:

- `output_count`: duplicated by `request_payload_json.outputCount`.
- `source_primary_asset_id`: replaced by `biz_material_assets`.
- `source_asset_ids_json`: replaced by `biz_material_assets`.
- `source_file_names_json`: replaced by `biz_material_assets`.
- `model_provider`: too coarse for multi-model pipelines; use request/model call rows.
- `plan_json`: planning output belongs in `context_json` or versioned artifacts.

`biz_task_attempts` tracks each execution attempt. It should be the source of truth for retry/continue/recover runs, queue ownership, and attempt terminal state.

`biz_task_stage_runs` tracks per-stage execution details. Its `status` is an internal `StageRunStatus`; provider statuses belong in `biz_task_model_calls` or stage output summary JSON.

`biz_task_queue_events` is append-only queue lifecycle data. It should be used for diagnosing scheduling and worker claim behavior rather than mutating attempt history.

`biz_worker_instances` tracks runtime worker registration and heartbeat state. Stale detection should be based on `status` and `last_heartbeat_at`.

`biz_task_status_history` records both status transitions and trace-only events. Because trace rows can have empty `previous_status` and `current_status`, status enum constraints should be introduced only after trace rows move to a dedicated trace table or receive a separate event type.

`biz_task_model_calls` records provider calls and should be kept for audit/debugging. It must not store material snapshots; task material mutations are persisted to `biz_material_assets`. The database constrains fields owned by this system, such as success flags, HTTP/business status codes, token counts, and durations. Long-term cleanup should remove duplicated model name columns after a single canonical shape is chosen.

`biz_request_logs` is the cross-cutting audit table for provider and backend operation requests. `request_type` must be non-blank; `success`, `http_status`, `duration_ms`, `timezone_offset_minutes`, and `is_deleted` are range-constrained. It is indexed by owner, task, workflow, and creation time so admin/debug views can inspect request history without scanning the whole table.

Video provider run polling should use `backend.domain.video_run_monitor` for active/success/failure classification and error extraction. Worker services should orchestrate polling and persistence instead of carrying provider status sets inline.

Provider media result URL extraction should use `backend.domain.media_result`. Worker services and material persistence should not duplicate `outputUrl`, `metadata.outputUrl`, `metadata.fileUrl`, and `metadata.remoteSourceUrl` fallback order.

Generation run kind/model kind constants and active/success status classification belong in `backend.domain.generation_run`. Generation services and provider integrations should reuse that boundary instead of introducing ad hoc run status sets.

Generation run artifact storage, MIME/extension inference, storage path defaults, and frontend URL expansion belong in `backend.services.generation_artifacts`. Run factories should orchestrate generation and metadata assembly instead of owning filesystem writes directly.

Generation run prompt shaping, script user prompts, model-info dictionaries, and media provider summary payloads belong in `backend.services.generation_payloads`. Run factories should call these pure builders instead of embedding prompt and observability dictionary shapes inline.

Generation request value parsing belongs in `backend.services.generation_request_values`. Generation orchestration should use these pure helpers for nested request reads, string normalization, and provider payload searches instead of growing utility methods inside `GenerationRunSupport`.

Provider response parsing for text, image, and video integrations belongs in `backend.services.model_response_parsing`. Transport classes should handle HTTP and request encoding; response shape fallback order should stay covered by pure unit tests.

JSON text column parsing and serialization belongs in `backend.domain.json_payloads`. Repositories and workflow services should use these helpers so malformed legacy JSON degrades to empty objects/lists instead of breaking list/detail/admin queries.

Task execution artifact/material/result row assembly belongs in `backend.services.task_artifact_assembler`. Worker pipeline services should orchestrate generation, status transitions, and persistence rather than constructing material/result dictionaries inline.

Task worker status transitions, stage-run rows, model-call rows, abort handling, and worker heartbeat mutations belong in `backend.services.task_worker_status_stage_service`. Worker pipeline services should call this boundary instead of directly building lifecycle rows.

Task execution runtime request building belongs in `backend.services.task_execution_runtime_support`. Dimensions, duration resolution, model selection, storage metadata, seed handling, and compatible reference-image URL expansion should be tested there instead of living inside the worker pipeline.

Task queue fairness belongs in `backend.domain.task_queue_fairness`. Queue coordinators and worker dispatch should reuse the round-robin scheduler instead of embedding owner interleaving logic in service classes.

Task queue enqueue lifecycle belongs to `TaskExecutionCoordinator` and command services because enqueueing must update the task row, active attempt, status history, and queue event atomically. `TaskQueueCoordinator` is the worker-side persisted queue port for `claim_next`, `remove`, and queue snapshots only; it must not expose a no-op enqueue shortcut.

Task monitoring snapshots belong in `backend.domain.task_monitoring`. Task list/detail views and admin diagnosis should use the same output, join, clip-continuity, active attempt, and worker summary rules.

Task worker API view mapping belongs in `backend.services.task_worker_view_mapper`. Worker pipeline services should not shape list/detail/showcase response dictionaries directly.

`biz_task_results` stores produced media outputs. The database constrains clip indexes, timing values, dimensions, and file sizes to non-negative ranges. It should reference material/model-call rows where possible and avoid storing the same URL under multiple names.

`biz_material_assets` is the media asset inventory and the canonical persistence target for material library, workflow assets, and `TaskPersistenceMutation.material_rows`. It currently has duplicated location fields:

- `local_storage_path` is the canonical local path for new writes; `local_file_path` is a legacy alias.
- `public_url` is the canonical frontend URL for new writes; `third_party_url` and `remote_url` are legacy/provider aliases.

The table is indexed by owner/media type, task/asset role, and workflow/stage/clip so library and workflow screens can query it without scanning all assets.

New write paths should populate `local_storage_path` and `public_url` first, then compatibility aliases only when older clients or provider payloads still require them. A later major schema version can remove duplicate location columns after the API compatibility layer is stable.

## Workflow Tables

`biz_stage_workflows` is the editable multi-stage generation aggregate. It owns workflow settings, stage progression, selected storyboard/final output pointers, and workflow-level rating.

Material reuse must create a persisted `biz_stage_workflows` row. Returning a temporary workflow-shaped response is not sufficient because the frontend navigates to the workflow detail route immediately after reuse.

User-facing workflow detail and mutation APIs must filter by `owner_user_id`. Cross-user or administrator workflow inspection should be added as an explicit admin API rather than reusing owner-scoped endpoints.

`WorkflowService` should own workflow mutations and orchestration. API response assembly belongs in `WorkflowViewMapper` so persistence rules, authorization checks, and view-shaping logic stay separately testable.

Workflow storyboard markdown parsing belongs in `backend.domain.workflow_storyboard_plan`; services should not duplicate table parsing rules or ad hoc markdown splitting.

Workflow generation-service payloads belong in `WorkflowGenerationRequestBuilder`. Services should orchestrate validation and persistence instead of hand-building provider request dictionaries inline.

Workflow generation-service responses belong in `WorkflowGenerationResultParser`. Services should not directly scatter `resultScript`, `resultImage`, or `resultVideo` shape checks across orchestration code. This applies to both synchronous create-run responses and asynchronous video refresh responses.

Workflow-owned ORM row defaults belong in `WorkflowPersistenceRowFactory`. In particular, `biz_material_assets` and `biz_stage_versions` row creation should not be duplicated across stage generation, async refresh, and finalization code paths.

`biz_stage_versions` stores versioned outputs for storyboard, keyframe, video, and joined stages. Its status field accepts both terminal version states and active provider states because video generation can be submitted asynchronously and refreshed later.

Workflow rows are indexed by `owner_user_id + status + is_deleted`. Stage versions are indexed by `workflow_id + stage_type + clip_index + is_deleted` for stage views and selection updates.

## Task Worker Boundaries

Task render-stage request/response objects, frame resolution values, stage-run payloads, and clip frame execution-context dictionaries belong in `TaskRenderStagePayloads`.

`TaskWorkerRenderStageService` lives in its own module and should orchestrate keyframe generation, video generation, artifact recording, and render-stage persistence only. The pipeline handler should stay focused on claim/resume, analysis, storyboard planning, and final completion wiring.

## Auth Tables

`sys_user.role` is a real authorization role, not a display label. Admin APIs should call `backend.auth.require_admin()`.

Bootstrap admin login is kept for local development, but production must set a strong bootstrap password and secret key. Bootstrap login now creates or restores an actual `sys_user` admin row, so administrator permissions are persisted in the database instead of living only in configuration.

JWT cookies are not the source of truth for authorization. Protected requests decode the token only to identify the subject, then re-read `sys_user.status` and `sys_user.role` so account disablement or admin demotion takes effect without waiting for token expiry.

`sys_user_model_credential` has a unique `user_id + provider_key` index. This matches the service upsert behavior and prevents duplicated provider credentials per user.

`sys_user_model_credential.encrypted_api_key` stores user-scoped provider keys encrypted with a key derived from `JIANDOU_SECRET_KEY`. The repository can still read legacy plaintext rows so existing local deployments can migrate by re-saving credentials.

## Credit Tables

`sys_credit_account` is the current balance row for one user and has non-negative balance/consumption constraints.

`sys_credit_rule` defines non-negative feature costs.

`sys_credit_transaction` is append-only ledger data. `amount_delta` is signed, while `balance_before` and `balance_after` must remain non-negative. Use transaction rows for audit history instead of mutating historical balance changes.

## Migration Plan

1. Add Alembic configuration and generate a baseline migration from the current schema.
2. Add comments, indexes, and non-breaking constraints for auth, credit, and workflow tables.
3. Backfill existing string status values to enum-compatible values.
4. Introduce typed datetime/boolean columns alongside legacy columns.
5. Update repositories and services to write canonical tables/columns first, with compatibility aliases only where required by existing clients.
6. Backfill data and switch reads to new columns.
7. Remove deprecated duplicate fields in a major schema migration.

Until Alembic is active, avoid destructive schema edits in ORM models.
