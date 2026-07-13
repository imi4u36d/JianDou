"""Build worker stage-run, model-call and provider trace records."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from backend.domain.task_record import TaskRecord
from backend.services.generation_service import GenerationProviderException
from backend.shared import first_non_blank, now_iso, string_value


def map_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


class TaskWorkerRecordFactory:
    def stage_run(
        self,
        task: TaskRecord,
        worker_instance_id: str,
        seq: int,
        stage_name: str,
        clip_index: int,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
    ) -> dict[str, Any]:
        timestamp = now_iso()
        return {
            "stageRunId": self._stable_id("stgrun", task.id, stage_name, str(clip_index)),
            "attemptId": task.active_attempt_id,
            "stageName": stage_name,
            "stageSeq": seq,
            "clipIndex": clip_index,
            "status": "COMPLETED",
            "workerInstanceId": worker_instance_id,
            "startedAt": timestamp,
            "finishedAt": timestamp,
            "durationMs": 0,
            "inputSummary": input_summary,
            "outputSummary": output_summary,
            "errorCode": "",
            "errorMessage": "",
        }

    def pending_model_call(
        self,
        task: TaskRecord,
        stage: str,
        operation: str,
        request_payload: dict[str, Any],
        clip_index: int,
        kind: str,
    ) -> dict[str, Any]:
        model_section = map_value(request_payload.get("model"))
        provider_model = first_non_blank(
            string_value(model_section.get("providerModel")),
            string_value(model_section.get("textAnalysisModel")),
        )
        call_id = self._stable_id("mdlcall", task.id, stage, kind, str(clip_index))
        timestamp = now_iso()
        return {
            "modelCallId": call_id,
            "requestLogId": f"reqlog_{call_id}",
            "callKind": stage,
            "stage": stage,
            "operation": operation,
            "provider": "generation",
            "providerModel": provider_model,
            "requestedModel": provider_model,
            "resolvedModel": "",
            "modelName": "",
            "modelAlias": provider_model,
            "endpointHost": "",
            "requestId": "",
            "requestPayload": request_payload,
            "responsePayload": {},
            "httpStatus": 0,
            "responseCode": 0,
            "success": False,
            "status": "pending",
            "errorCode": "",
            "errorMessage": "",
            "latencyMs": 0,
            "durationMs": 0,
            "inputTokens": 0,
            "outputTokens": 0,
            "startedAt": timestamp,
            "finishedAt": timestamp,
        }

    def complete_model_call(
        self,
        pending_model_call: dict[str, Any],
        run: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        row = dict(pending_model_call or {})
        model_info = map_value(result.get("modelInfo"))
        started_at = string_value(row.get("startedAt"))
        finished_at = string_value(run.get("updatedAt", now_iso()))
        row.update(
            {
                "provider": string_value(model_info.get("provider", row.get("provider"))),
                "providerModel": first_non_blank(
                    string_value(model_info.get("providerModel")), string_value(row.get("providerModel"))
                ),
                "requestedModel": first_non_blank(
                    string_value(model_info.get("requestedModel")), string_value(row.get("requestedModel"))
                ),
                "resolvedModel": string_value(model_info.get("resolvedModel")),
                "modelName": string_value(model_info.get("modelName", model_info.get("resolvedModel"))),
                "modelAlias": string_value(model_info.get("modelName", model_info.get("resolvedModel"))),
                "endpointHost": string_value(model_info.get("endpointHost")),
                "requestId": string_value(run.get("id")),
                "responsePayload": {"runId": string_value(run.get("id")), "result": result},
                "httpStatus": 200,
                "responseCode": 200,
                "success": True,
                "status": "success",
                "errorCode": "",
                "errorMessage": "",
                "latencyMs": 0,
                "durationMs": self._duration_millis(started_at, finished_at),
                "finishedAt": finished_at,
            }
        )
        return row

    def fail_model_call(
        self,
        pending_model_call: dict[str, Any],
        error: Exception,
    ) -> dict[str, Any]:
        row = dict(pending_model_call or {})
        finished_at = now_iso()
        http_status = error.http_status if isinstance(error, GenerationProviderException) else 0
        response_payload: dict[str, Any] = {
            "errorType": error.__class__.__name__ if error else "",
            "errorMessage": first_non_blank(str(error) if error else "", "unknown"),
        }
        if isinstance(error, GenerationProviderException):
            response_payload.update(
                {
                    "providerRequest": error.provider_request,
                    "providerResponse": error.provider_response,
                    "httpStatus": error.http_status,
                }
            )
        row.update(
            {
                "responsePayload": response_payload,
                "httpStatus": max(0, http_status),
                "responseCode": max(0, http_status),
                "success": False,
                "status": "failed",
                "errorCode": error.__class__.__name__ if error else "",
                "errorMessage": first_non_blank(str(error) if error else "", "unknown"),
                "durationMs": self._duration_millis(string_value(row.get("startedAt")), finished_at),
                "finishedAt": finished_at,
            }
        )
        return row

    def run_call_chain(
        self,
        fallback_stage: str,
        run: dict[str, Any],
        result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        raw = result.get("callChain")
        if not isinstance(raw, list):
            return []
        rows: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            status = string_value(item.get("status"))
            rows.append(
                {
                    "stage": string_value(item.get("stage")) or fallback_stage,
                    "event": string_value(item.get("event")) or "generation.call",
                    "message": string_value(item.get("message")) or "generation run completed",
                    "level": "INFO" if status.lower() == "success" else "WARN",
                    "payload": {
                        "runId": string_value(run.get("id")),
                        "status": status,
                        "details": map_value(item.get("details")),
                    },
                }
            )
        return rows

    @staticmethod
    def _stable_id(prefix: str, *parts: str) -> str:
        seed = prefix + ":" + ":".join(parts)
        return prefix + "_" + uuid.uuid5(uuid.NAMESPACE_OID, seed).hex

    @staticmethod
    def _duration_millis(started_at: str, finished_at: str) -> int:
        try:
            start = datetime.fromisoformat(started_at)
            end = datetime.fromisoformat(finished_at)
            return max(0, int((end - start).total_seconds() * 1000))
        except (ValueError, TypeError):
            return 0
