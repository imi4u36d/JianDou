"""Pure task diagnosis rules and response projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.domain.task_monitoring import latest_join_output_of, latest_video_output_of, missing_clip_indices
from backend.domain.task_result_types import is_join, is_primary_video
from backend.shared import first_non_blank, map_value, string_value

_SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
_TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED"})


@dataclass(frozen=True)
class TaskDiagnosisSnapshot:
    task_id: Any
    title: Any
    status: str
    error_message: Any
    is_queued: bool
    queue_position: Any
    monitoring: dict[str, Any]
    outputs: list[dict[str, Any]]
    rendered_clip_indices: list[int]


@dataclass(frozen=True)
class TaskFinding:
    code: str
    severity: str
    title: str
    detail: str

    def to_map(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class _DiagnosisFacts:
    planned_clip_count: int
    contiguous_rendered_clip_count: int
    latest_rendered_clip_index: int
    missing_indices: list[int]
    latest_join_output: dict[str, Any]
    latest_video_output: dict[str, Any]
    join_count: int
    video_clip_count: int
    has_audio_clip: bool


class TaskDiagnosisRules:
    """Evaluate task health without repository or model dependencies."""

    def diagnose(self, snapshot: TaskDiagnosisSnapshot) -> dict[str, Any]:
        facts = self._facts(snapshot)
        findings = self._findings(snapshot, facts)
        monitoring = snapshot.monitoring
        latest_video_extra = map_value(facts.latest_video_output.get("extra"))

        return {
            "taskId": snapshot.task_id,
            "title": snapshot.title,
            "status": snapshot.status,
            "severity": self._highest_severity(findings),
            "summary": self._summary(findings, facts),
            "findings": [finding.to_map() for finding in findings],
            "recovery": {
                "canRetry": snapshot.status not in ("RENDERING", "ANALYZING", "PLANNING"),
                "recommendedAction": self._recommended_action(snapshot, findings, facts),
                "resumeFromStage": monitoring.get("resumeFromStage"),
                "resumeFromClipIndex": _int_value(
                    monitoring.get("resumeFromClipIndex"),
                    max(1, facts.contiguous_rendered_clip_count + 1),
                ),
            },
            "continuity": {
                "plannedClipCount": facts.planned_clip_count,
                "renderedClipIndices": snapshot.rendered_clip_indices,
                "contiguousRenderedClipCount": facts.contiguous_rendered_clip_count,
                "missingClipIndices": facts.missing_indices,
                "latestRenderedClipIndex": facts.latest_rendered_clip_index,
                "latestJoinName": string_value(monitoring.get("latestJoinName")),
                "latestJoinClipIndex": _int_value(
                    monitoring.get("latestJoinClipIndex"),
                    _int_value(facts.latest_join_output.get("clipIndex"), 0),
                ),
                "latestJoinClipIndices": _list_value(monitoring.get("latestJoinClipIndices")),
            },
            "outputs": {
                "videoClipCount": facts.video_clip_count,
                "joinCount": facts.join_count,
                "latestVideoOutputUrl": first_non_blank(
                    string_value(monitoring.get("latestVideoOutputUrl")),
                    string_value(facts.latest_video_output.get("downloadUrl")),
                ),
                "latestJoinOutputUrl": first_non_blank(
                    string_value(monitoring.get("latestJoinOutputUrl")),
                    string_value(facts.latest_join_output.get("downloadUrl")),
                ),
                "latestLastFrameUrl": string_value(latest_video_extra.get("lastFrameUrl")),
                "hasAudioClip": facts.has_audio_clip,
            },
            "queue": {
                "isQueued": snapshot.is_queued,
                "queuePosition": snapshot.queue_position,
                "activeAttemptStatus": monitoring.get("activeAttemptStatus"),
                "activeWorkerInstanceId": monitoring.get("activeWorkerInstanceId"),
            },
        }

    def severity(self, snapshot: TaskDiagnosisSnapshot) -> str:
        facts = self._facts(snapshot)
        levels: list[str] = []
        if snapshot.status == "FAILED" or (snapshot.status == "PENDING" and not snapshot.is_queued):
            levels.append("high")
        if facts.planned_clip_count > 0 and facts.contiguous_rendered_clip_count < facts.planned_clip_count:
            levels.append("high" if _is_terminal(snapshot.status) else "medium")
        if facts.video_clip_count > 1 and facts.join_count == 0:
            levels.append("medium")
        if (
            snapshot.status == "COMPLETED"
            and facts.planned_clip_count > 0
            and facts.video_clip_count < facts.planned_clip_count
        ):
            levels.append("high")
        return max(levels, key=lambda level: _SEVERITY_RANK.get(level, 0), default="info")

    @staticmethod
    def _facts(snapshot: TaskDiagnosisSnapshot) -> _DiagnosisFacts:
        monitoring = snapshot.monitoring
        planned_clip_count = _int_value(monitoring.get("plannedClipCount"), 0)
        latest_join_output = latest_join_output_of(snapshot.outputs)
        latest_video_output = latest_video_output_of(snapshot.outputs)
        return _DiagnosisFacts(
            planned_clip_count=planned_clip_count,
            contiguous_rendered_clip_count=_int_value(monitoring.get("contiguousRenderedClipCount"), 0),
            latest_rendered_clip_index=_int_value(monitoring.get("latestRenderedClipIndex"), 0),
            missing_indices=missing_clip_indices(planned_clip_count, snapshot.rendered_clip_indices),
            latest_join_output=latest_join_output,
            latest_video_output=latest_video_output,
            join_count=sum(1 for item in snapshot.outputs if is_join(item.get("resultType"))),
            video_clip_count=len(snapshot.rendered_clip_indices),
            has_audio_clip=any(
                _bool_value(map_value(item.get("extra")).get("hasAudio"))
                for item in snapshot.outputs
                if is_primary_video(item.get("resultType"))
            ),
        )

    def _findings(self, snapshot: TaskDiagnosisSnapshot, facts: _DiagnosisFacts) -> list[TaskFinding]:
        findings: list[TaskFinding] = []
        if snapshot.status == "FAILED":
            findings.append(TaskFinding(
                "task_failed",
                "high",
                "Task status is FAILED",
                first_non_blank(string_value(snapshot.error_message), "Check the most recent trace and model call records."),
            ))
        if snapshot.status == "PENDING" and not snapshot.is_queued:
            findings.append(TaskFinding(
                "pending_not_queued",
                "high",
                "Task status is PENDING but not queued",
                "This usually means attempt/queue state is out of sync; re-enqueue or retry.",
            ))
        if facts.planned_clip_count > 0 and facts.contiguous_rendered_clip_count < facts.planned_clip_count:
            findings.append(TaskFinding(
                "missing_clips",
                "high" if _is_terminal(snapshot.status) else "medium",
                "Clip output does not fully cover planned shots",
                f"Continuous clips: {facts.contiguous_rendered_clip_count}/{facts.planned_clip_count}, missing: {facts.missing_indices}",
            ))
        if facts.video_clip_count > 1 and facts.join_count == 0:
            findings.append(TaskFinding(
                "join_missing",
                "medium",
                "Multi-clip task has no join output yet",
                f"{facts.video_clip_count} clips rendered but no join output.",
            ))
        if facts.video_clip_count > 0 and not facts.has_audio_clip:
            findings.append(TaskFinding(
                "audio_missing",
                "medium",
                "Video clip has no detected audio track",
                "Check the remote video model response and generateAudio parameter.",
            ))
        if (
            snapshot.status == "COMPLETED"
            and facts.planned_clip_count > 0
            and facts.video_clip_count < facts.planned_clip_count
        ):
            findings.append(TaskFinding(
                "completed_but_incomplete",
                "high",
                "Task marked COMPLETED but clips not fully generated",
                "COMPLETED status inconsistent with clip output count.",
            ))
        return findings or [TaskFinding("healthy", "info", "No issues detected", "Task status, queue, and clip output appear consistent.")]

    def _summary(self, findings: list[TaskFinding], facts: _DiagnosisFacts) -> str:
        highest = self._highest_severity(findings)
        if highest == "high":
            return "Task has high-priority issues; check failure reason and recovery starting point."
        if highest == "medium":
            return "Main pipeline is running but there are completeness or join consistency risks."
        return f"Task is healthy. Planned clips: {facts.planned_clip_count}, video clips: {facts.video_clip_count}, joins: {facts.join_count}."

    @staticmethod
    def _recommended_action(
        snapshot: TaskDiagnosisSnapshot,
        findings: list[TaskFinding],
        facts: _DiagnosisFacts,
    ) -> str:
        if snapshot.status == "FAILED":
            return (
                "Retry; resume from the failed clip with existing clips."
                if facts.contiguous_rendered_clip_count > 0
                else "Retry; restart from the analysis phase."
            )
        if snapshot.status == "PAUSED":
            return "Continue; keep current clip progress."
        if facts.planned_clip_count > 1 and any(finding.code == "join_missing" for finding in findings):
            return "Check join worker trace; re-trigger join once clips are contiguous."
        if snapshot.status == "PENDING" and not snapshot.is_queued:
            return "Re-enqueue the task; retry to create a new attempt if needed."
        return "Monitor latest trace and stage run; retry if no progress for an extended period."

    @staticmethod
    def _highest_severity(findings: list[TaskFinding]) -> str:
        return max(
            (finding.severity for finding in findings),
            key=lambda level: _SEVERITY_RANK.get(level, 0),
            default="info",
        )


def _is_terminal(status: str) -> bool:
    return status.upper() in _TERMINAL_STATUSES


def _list_value(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _int_value(value: object, fallback: int = 0) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if value is not None:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return string_value(value).lower() in ("true", "1", "yes")
