"""Task diagnosis service — analyzes task state for issues, continuity, and recovery.

Mirrors the Java TaskDiagnosisService, TaskQueueFairScheduler, TaskQueueCoordinator,
and TaskRequestSnapshotFactory classes.
"""

from __future__ import annotations

from typing import Any

from backend.domain import task_queue_fairness
from backend.domain.request_snapshot import (
    GenerationRequestSnapshot,
    RequestedDuration,
    RequestedOutputCount,
)
from backend.domain.task_monitoring import (
    latest_join_output_of,
    latest_video_output_of,
    task_monitoring_snapshot,
    task_outputs,
)
from backend.domain.task_monitoring import (
    missing_clip_indices as monitoring_missing_clip_indices,
)
from backend.domain.task_result_types import is_join, is_primary_video
from backend.domain.task_resume import existing_video_clip_indices
from backend.shared import first_non_blank, map_value, string_value

OwnerResolver = task_queue_fairness.OwnerResolver
TaskQueueFairScheduler = task_queue_fairness.TaskQueueFairScheduler

__all__ = [
    "OwnerResolver",
    "TaskDiagnosisService",
    "TaskQueueCoordinator",
    "TaskQueueFairScheduler",
    "TaskRequestSnapshotFactory",
]

# ===========================================================================
# Utility helpers
# ===========================================================================

_SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}

_TASK_STATUS_TERMINAL = frozenset({"COMPLETED", "FAILED"})


def _is_terminal(status: str) -> bool:
    return status.upper() in _TASK_STATUS_TERMINAL



def _list_value(value: object) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    return []



def _int_value(value: object, fallback: int = 0) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if value is not None:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _integer_value(value: object) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if value is not None:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            pass
    return None


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    v = string_value(value).lower()
    return v in ("true", "1", "yes")



def _trimmed(value: str | None, fallback: str) -> str:
    if value is None:
        return fallback
    v = value.strip()
    return v if v else fallback


# ===========================================================================
# TaskFinding
# ===========================================================================


class TaskFinding:
    """A single diagnosis finding with code, severity, title, and detail."""

    def __init__(self, code: str, severity: str, title: str, detail: str) -> None:
        self._code = code
        self._severity = severity
        self._title = title
        self._detail = detail

    @property
    def code(self) -> str:
        return self._code

    @property
    def severity(self) -> str:
        return self._severity

    def to_map(self) -> dict[str, Any]:
        return {
            "code": self._code,
            "severity": self._severity,
            "title": self._title,
            "detail": self._detail,
        }


# ===========================================================================
# TaskDiagnosisService
# ===========================================================================


class TaskDiagnosisService:
    """Diagnoses task state, continuity, and product completeness.

    Mirrors the Java TaskDiagnosisService.  Each diagnosis run produces a
    structured dict with findings, recovery hints, continuity info, output
    summaries, and queue status.
    """

    def diagnose(self, task: Any) -> dict[str, Any]:
        """Run full diagnosis on a task and return a structured diagnosis dict."""
        monitoring = self._monitoring_snapshot(task)
        rendered_clip_indices = self._existing_video_clip_indices(task)
        planned_clip_count = _int_value(monitoring.get("plannedClipCount"), 0)
        contiguous_rendered_clip_count = _int_value(monitoring.get("contiguousRenderedClipCount"), 0)
        latest_rendered_clip_index = _int_value(monitoring.get("latestRenderedClipIndex"), 0)
        missing_indices = self._missing_clip_indices(planned_clip_count, rendered_clip_indices)
        outputs_view = self._get_outputs_view(task)
        latest_join_output = self._latest_output_of_kind(task, "video_join")
        latest_video_output = self._latest_output_of_kind(task, "video")
        latest_video_extra = map_value(latest_video_output.get("extra"))

        join_count = sum(1 for item in outputs_view if is_join(item.get("resultType")))
        video_clip_count = len(rendered_clip_indices)
        has_audio_clip = any(
            _bool_value(map_value(item.get("extra")).get("hasAudio"))
            for item in outputs_view
            if is_primary_video(item.get("resultType"))
        )

        findings: list[TaskFinding] = []
        task_status = string_value(getattr(task, "status", ""))

        if task_status == "FAILED":
            findings.append(TaskFinding(
                "task_failed", "high",
                "Task status is FAILED",
                first_non_blank(
                    string_value(getattr(task, "error_message", None)),
                    "Check the most recent trace and model call records.",
                ),
            ))

        if task_status == "PENDING" and not getattr(task, "is_queued", False):
            findings.append(TaskFinding(
                "pending_not_queued", "high",
                "Task status is PENDING but not queued",
                "This usually means attempt/queue state is out of sync; re-enqueue or retry.",
            ))

        if planned_clip_count > 0 and contiguous_rendered_clip_count < planned_clip_count:
            findings.append(TaskFinding(
                "missing_clips",
                "high" if _is_terminal(task_status) else "medium",
                "Clip output does not fully cover planned shots",
                f"Continuous clips: {contiguous_rendered_clip_count}/{planned_clip_count}, missing: {missing_indices}",
            ))

        if video_clip_count > 1 and join_count == 0:
            findings.append(TaskFinding(
                "join_missing", "medium",
                "Multi-clip task has no join output yet",
                f"{video_clip_count} clips rendered but no join output.",
            ))

        if video_clip_count > 0 and not has_audio_clip:
            findings.append(TaskFinding(
                "audio_missing", "medium",
                "Video clip has no detected audio track",
                "Check the remote video model response and generateAudio parameter.",
            ))

        if task_status == "COMPLETED" and planned_clip_count > 0 and video_clip_count < planned_clip_count:
            findings.append(TaskFinding(
                "completed_but_incomplete", "high",
                "Task marked COMPLETED but clips not fully generated",
                "COMPLETED status inconsistent with clip output count.",
            ))

        if not findings:
            findings.append(TaskFinding(
                "healthy", "info",
                "No issues detected",
                "Task status, queue, and clip output appear consistent.",
            ))

        recommended_action = self._recommended_action(
            task, findings, contiguous_rendered_clip_count, planned_clip_count,
        )

        recovery: dict[str, Any] = {
            "canRetry": task_status not in ("RENDERING", "ANALYZING", "PLANNING"),
            "recommendedAction": recommended_action,
            "resumeFromStage": monitoring.get("resumeFromStage"),
            "resumeFromClipIndex": _int_value(
                monitoring.get("resumeFromClipIndex"),
                max(1, contiguous_rendered_clip_count + 1),
            ),
        }

        continuity: dict[str, Any] = {
            "plannedClipCount": planned_clip_count,
            "renderedClipIndices": rendered_clip_indices,
            "contiguousRenderedClipCount": contiguous_rendered_clip_count,
            "missingClipIndices": missing_indices,
            "latestRenderedClipIndex": latest_rendered_clip_index,
            "latestJoinName": string_value(monitoring.get("latestJoinName")),
            "latestJoinClipIndex": _int_value(
                monitoring.get("latestJoinClipIndex"),
                _int_value(latest_join_output.get("clipIndex"), 0),
            ),
            "latestJoinClipIndices": _list_value(monitoring.get("latestJoinClipIndices")),
        }

        outputs: dict[str, Any] = {
            "videoClipCount": video_clip_count,
            "joinCount": join_count,
            "latestVideoOutputUrl": first_non_blank(
                string_value(monitoring.get("latestVideoOutputUrl")),
                string_value(latest_video_output.get("downloadUrl")),
            ),
            "latestJoinOutputUrl": first_non_blank(
                string_value(monitoring.get("latestJoinOutputUrl")),
                string_value(latest_join_output.get("downloadUrl")),
            ),
            "latestLastFrameUrl": string_value(latest_video_extra.get("lastFrameUrl")),
            "hasAudioClip": has_audio_clip,
        }

        queue: dict[str, Any] = {
            "isQueued": bool(getattr(task, "is_queued", False)),
            "queuePosition": getattr(task, "queue_position", None),
            "activeAttemptStatus": monitoring.get("activeAttemptStatus"),
            "activeWorkerInstanceId": monitoring.get("activeWorkerInstanceId"),
        }

        severity = self._highest_severity(findings)
        summary = self._diagnosis_summary(findings, planned_clip_count, video_clip_count, join_count)

        return {
            "taskId": getattr(task, "id", ""),
            "title": getattr(task, "title", ""),
            "status": task_status,
            "severity": severity,
            "summary": summary,
            "findings": [f.to_map() for f in findings],
            "recovery": recovery,
            "continuity": continuity,
            "outputs": outputs,
            "queue": queue,
        }

    def severity(self, task: Any) -> str:
        """Return the highest severity level across all findings."""
        # Quick check without running full diagnosis
        monitoring = self._monitoring_snapshot(task)
        rendered = self._existing_video_clip_indices(task)
        planned = _int_value(monitoring.get("plannedClipCount"), 0)
        contiguous = _int_value(monitoring.get("contiguousRenderedClipCount"), 0)
        task_status = string_value(getattr(task, "status", ""))

        findings: list[TaskFinding] = []
        if task_status == "FAILED":
            findings.append(TaskFinding("", "high", "", ""))
        if task_status == "PENDING" and not getattr(task, "is_queued", False):
            findings.append(TaskFinding("", "high", "", ""))
        if planned > 0 and contiguous < planned:
            findings.append(TaskFinding("", "high" if _is_terminal(task_status) else "medium", "", ""))
        if len(rendered) > 1:
            join_count = sum(1 for item in self._get_outputs_view(task) if is_join(item.get("resultType")))
            if join_count == 0:
                findings.append(TaskFinding("", "medium", "", ""))
        if task_status == "COMPLETED" and planned > 0 and len(rendered) < planned:
            findings.append(TaskFinding("", "high", "", ""))
        return self._highest_severity(findings) if findings else "info"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_outputs_view(self, task: Any) -> list[dict[str, Any]]:
        return task_outputs(task)

    def _latest_output_of_kind(self, task: Any, result_type: str) -> dict[str, Any]:
        outputs = self._get_outputs_view(task)
        if result_type == "video":
            return latest_video_output_of(outputs)
        if result_type == "video_join":
            return latest_join_output_of(outputs)
        matching = [item for item in outputs if result_type == string_value(item.get("resultType")).lower()]
        matching.sort(key=lambda item: _int_value(item.get("clipIndex"), 0))
        return matching[-1] if matching else {}

    def _missing_clip_indices(self, planned_clip_count: int, rendered_clip_indices: list[int]) -> list[int]:
        return monitoring_missing_clip_indices(planned_clip_count, rendered_clip_indices)

    def _monitoring_snapshot(self, task: Any) -> dict[str, Any]:
        monitoring = task_monitoring_snapshot(task)
        legacy = getattr(task, "monitoring", None)
        if isinstance(legacy, dict):
            monitoring.update({key: value for key, value in legacy.items() if value not in (None, "", [])})
        return monitoring

    def _highest_severity(self, findings: list[TaskFinding]) -> str:
        level = 0
        label = "info"
        for finding in findings:
            current = _SEVERITY_RANK.get(finding.severity, 0)
            if current > level:
                level = current
                label = finding.severity if finding.severity else "info"
        return label

    def _diagnosis_summary(
        self,
        findings: list[TaskFinding],
        planned_clip_count: int,
        video_clip_count: int,
        join_count: int,
    ) -> str:
        highest = self._highest_severity(findings)
        if highest == "high":
            return "Task has high-priority issues; check failure reason and recovery starting point."
        if highest == "medium":
            return "Main pipeline is running but there are completeness or join consistency risks."
        return f"Task is healthy. Planned clips: {planned_clip_count}, video clips: {video_clip_count}, joins: {join_count}."

    def _recommended_action(
        self,
        task: Any,
        findings: list[TaskFinding],
        contiguous_rendered_clip_count: int,
        planned_clip_count: int,
    ) -> str:
        task_status = string_value(getattr(task, "status", ""))
        if task_status == "FAILED":
            return ("Retry; resume from the failed clip with existing clips."
                    if contiguous_rendered_clip_count > 0
                    else "Retry; restart from the analysis phase.")
        if task_status == "PAUSED":
            return "Continue; keep current clip progress."
        if planned_clip_count > 1 and any(f.code == "join_missing" for f in findings):
            return "Check join worker trace; re-trigger join once clips are contiguous."
        if task_status == "PENDING" and not getattr(task, "is_queued", False):
            return "Re-enqueue the task; retry to create a new attempt if needed."
        return "Monitor latest trace and stage run; retry if no progress for an extended period."

    def _existing_video_clip_indices(self, task: Any) -> list[int]:
        return existing_video_clip_indices(self._get_outputs_view(task))


# ===========================================================================
# TaskQueueCoordinator
# ===========================================================================


class TaskQueueCoordinator:
    """Coordinates worker-side operations for the persisted task queue.

    Mirrors the Java TaskQueueCoordinator infrastructure class.
    Queue entries are derived from persisted task attempts. Enqueue lifecycle
    mutations must go through TaskExecutionCoordinator and TaskCommandService.
    """

    SNAPSHOT_LIMIT = 500

    def __init__(self, task_repository: Any) -> None:
        self._task_repository = task_repository

    async def remove(self, task_id: str) -> None:
        """Remove a task from the queue."""
        await self._task_repository.remove_queued_task(task_id)

    async def claim_next(self, worker_instance_id: str) -> str | None:
        """Claim the next queued task for a worker."""
        return await self._task_repository.claim_next_queued_task(worker_instance_id)

    async def snapshot(self) -> list[str]:
        """Return a snapshot of queued task IDs."""
        return await self._task_repository.list_queued_task_ids(self.SNAPSHOT_LIMIT)


# ===========================================================================
# TaskRequestSnapshotFactory
# ===========================================================================


class TaskRequestSnapshotFactory:
    """Creates immutable snapshots of generation requests at task creation time.

    Mirrors the Java TaskRequestSnapshotFactory application component.
    """

    def __init__(self, model_resolver: Any) -> None:
        self._model_resolver = model_resolver

    def create(self, request: Any, task: Any) -> GenerationRequestSnapshot:
        """Build a GenerationRequestSnapshot from a request and task record."""
        task_type = self._normalized_task_type(
            string_value(task.task_type if task is not None else ""),
            string_value(getattr(request, "task_type", None) if hasattr(request, "task_type") else
                          getattr(request, "taskType", None)),
        )

        return GenerationRequestSnapshot(
            task_type=task_type,
            asset_type=self._normalized_asset_type(
                string_value(getattr(request, "asset_type", None) if hasattr(request, "asset_type") else
                              getattr(request, "assetType", None)),
                task_type,
            ),
            title=string_value(getattr(task, "title", "")),
            creative_prompt=string_value(getattr(task, "creative_prompt", getattr(task, "creativePrompt", ""))),
            aspect_ratio=string_value(getattr(task, "aspect_ratio", getattr(task, "aspectRatio", ""))),
            image_size=_trimmed(
                getattr(request, "image_size", None) if hasattr(request, "image_size") else
                getattr(request, "imageSize", None),
                "",
            ),
            style_preset=first_non_blank(
                self._model_resolver_value("catalog.defaults", "style_preset", "cinematic"),
                "cinematic",
            ),
            text_analysis_model=_trimmed(
                getattr(request, "text_analysis_model", None) if hasattr(request, "text_analysis_model") else
                getattr(request, "textAnalysisModel", None),
                "",
            ),
            image_model=_trimmed(
                getattr(request, "image_model", None) if hasattr(request, "image_model") else
                getattr(request, "imageModel", None),
                "",
            ),
            video_model=_trimmed(
                getattr(request, "video_model", None) if hasattr(request, "video_model") else
                getattr(request, "videoModel", None),
                "",
            ),
            video_size=_trimmed(
                getattr(request, "video_size", None) if hasattr(request, "video_size") else
                getattr(request, "videoSize", None),
                self._model_resolver_value("catalog.defaults", "video_size", "720*1280"),
            ),
            seed=getattr(task, "task_seed", getattr(task, "taskSeed", None)),
            video_duration=RequestedDuration.from_raw(
                getattr(request, "video_duration_seconds", None) if hasattr(request, "video_duration_seconds") else
                getattr(request, "videoDurationSeconds", None),
            ),
            output_count=RequestedOutputCount.from_raw(
                self._normalize_output_count(
                    getattr(request, "output_count", None) if hasattr(request, "output_count") else
                    getattr(request, "outputCount", None),
                ),
            ),
            min_duration_seconds=_int_value(getattr(task, "min_duration_seconds", getattr(task, "minDurationSeconds", 0)), 0),
            max_duration_seconds=_int_value(getattr(task, "max_duration_seconds", getattr(task, "maxDurationSeconds", 0)), 0),
            transcript_text=string_value(getattr(task, "transcript_text", getattr(task, "transcriptText", ""))),
            stop_before_video_generation=bool(
                getattr(request, "stop_before_video_generation", None) if hasattr(request, "stop_before_video_generation") else
                getattr(request, "stopBeforeVideoGeneration", None) or False
            ),
        )

    def request_snapshot_output_count(self, task: Any) -> int:
        """Return the resolved output count from a task's request snapshot."""
        snapshot = getattr(task, "request_snapshot", None) or {}
        raw = snapshot.get("outputCount") if isinstance(snapshot, dict) else None
        if raw is None:
            return 1
        if isinstance(raw, (int, float)):
            return max(1, int(raw))
        return 1

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _model_resolver_value(self, section: str, key: str, fallback: str) -> str:
        if self._model_resolver is not None and hasattr(self._model_resolver, "value"):
            try:
                result = self._model_resolver.value(section, key, fallback)
                if result is not None:
                    return string_value(result)
            except Exception:  # noqa: S110 — best-effort config resolution
                pass
        return fallback

    @staticmethod
    def _normalized_task_type(task_value: str, request_value: str) -> str:
        normalized = first_non_blank(request_value, task_value, "generation")
        if not request_value and normalized == "video_generation":
            return "generation"
        valid = {"image_generation", "image_to_image", "character_sheet", "video_generation", "generation"}
        if normalized in valid:
            return normalized
        return normalized

    @staticmethod
    def _normalized_asset_type(asset_type: str, task_type: str) -> str:
        if asset_type:
            return asset_type
        return "character_sheet" if task_type == "character_sheet" else "free"

    @staticmethod
    def _normalize_output_count(output_count: object) -> object:
        if output_count is None:
            return "auto"
        raw = string_value(output_count)
        if not raw or raw.lower() == "auto":
            return "auto"
        try:
            value = int(raw)
            if value < 1:
                raise ValueError("outputCount must be greater than 0")
            return value
        except (ValueError, TypeError) as ex:
            if isinstance(ex, ValueError) and "must be greater than 0" in str(ex):
                raise
            raise ValueError("outputCount must be a positive integer or 'auto'")
