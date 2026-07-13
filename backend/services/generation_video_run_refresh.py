"""Asynchronous provider refresh state machine for video generation runs."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from backend.domain.generation_run import GenerationModelKinds, GenerationRunKinds, GenerationRunStatuses
from backend.domain.video_run_monitor import is_permanent_provider_error
from backend.services.generation_run_support import GenerationRunSupport

logger = logging.getLogger(__name__)

MediaProfileResolver = Callable[[str, str, int | None], dict[str, Any]]
VideoQuery = Callable[[dict[str, Any], str], Awaitable[dict[str, Any]]]


class GenerationVideoRunRefresher:
    """Advance active video runs from provider query responses."""

    _SUCCESS_STATES = {"SUCCEEDED", "SUCCESS", "DONE", "COMPLETED", "FINISHED"}
    _FAILED_STATES = {"FAILED", "FAIL", "CANCELED", "CANCELLED", "ERROR"}

    def __init__(
        self,
        support: GenerationRunSupport,
        resolve_media_profile: MediaProfileResolver,
        call_video_query: VideoQuery,
    ) -> None:
        self._support = support
        self._resolve_media_profile = resolve_media_profile
        self._call_video_query = call_video_query

    async def refresh(self, run: dict[str, Any]) -> dict[str, Any]:
        if self._support.string_value(run.get("kind")).lower() != GenerationRunKinds.VIDEO:
            return run
        if not GenerationRunStatuses.is_active(self._support.string_value(run.get("status")).lower()):
            return run
        result = self._support.map_value(run.get("result"))
        if not result:
            return run
        metadata = self._support.map_value(result.get("metadata"))
        task_id = self._support.string_value(metadata.get("taskId"))
        requested_model = self._support.first_non_blank(
            self._support.string_value(metadata.get("requestedModel")),
            self._support.string_value(metadata.get("providerModel")),
        )
        if not task_id or not requested_model:
            return run
        now_ms = datetime.now(UTC).timestamp() * 1000
        next_poll_at = metadata.get("nextPollAt", 0)
        if isinstance(next_poll_at, (int, float)) and next_poll_at > now_ms:
            return run

        profile = self._resolve_media_profile(
            requested_model,
            GenerationModelKinds.VIDEO,
            self._user_id_from_run(run),
        )
        call_chain = self._mutable_call_chain(result.get("callChain"))
        query = await self._query_provider(profile, task_id)
        query_status = query["taskStatus"]
        task_message = query["taskMessage"]
        provider_response = query["providerResponse"]

        if is_permanent_provider_error(task_message, provider_response):
            error = self._error_message(task_message, provider_response, query_status)
            metadata.update(
                taskStatus="FAILED",
                taskMessage=task_message,
                error=error,
                providerPayload=provider_response,
                nextPollAt=None,
            )
            self._record_query(metadata, profile, query, success=False)
            self._append_status_log(call_chain, "video.failed", "error", task_id, "FAILED", error)
            result["error"] = error
            return self._finish(run, result, metadata, call_chain, GenerationRunStatuses.FAILED)

        metadata.update(
            taskStatus=query_status,
            taskMessage=task_message,
            providerPayload=provider_response,
        )
        self._record_query(metadata, profile, query, success=query_status in self._SUCCESS_STATES)

        if query_status in self._SUCCESS_STATES:
            artifact = self._materialize(run, metadata, query["videoUrl"])
            result["outputUrl"] = artifact["publicUrl"]
            result["mimeType"] = artifact["mimeType"]
            result["hasAudio"] = self._support.nested_boolean(
                {"meta": metadata}, "meta", "generateAudio", True
            )
            metadata.update(
                outputUrl=artifact["publicUrl"],
                fileUrl=artifact["publicUrl"],
                remoteSourceUrl=query["videoUrl"],
                providerLastFrameUrl="",
                lastFrameUrl=self._support.string_value(metadata.get("requestedLastFrameUrl")),
                nextPollAt=None,
            )
            metadata["last_frame_url"] = metadata["lastFrameUrl"]
            self._append_status_log(
                call_chain,
                "video.completed",
                "success",
                task_id,
                query_status,
                "",
                output_url=artifact["publicUrl"],
            )
            return self._finish(run, result, metadata, call_chain, GenerationRunStatuses.SUCCEEDED)

        if query_status in self._FAILED_STATES:
            error = self._error_message(task_message, provider_response, query_status)
            result["error"] = error
            metadata.update(error=error, nextPollAt=None)
            self._append_status_log(call_chain, "video.failed", "error", task_id, query_status, error)
            return self._finish(run, result, metadata, call_chain, GenerationRunStatuses.FAILED)

        metadata["nextPollAt"] = now_ms + 5000
        self._append_status_log(call_chain, "video.polling", "running", task_id, query_status, "")
        return self._finish(run, result, metadata, call_chain, GenerationRunStatuses.RUNNING)

    async def _query_provider(self, profile: dict[str, Any], task_id: str) -> dict[str, Any]:
        try:
            response = await self._call_video_query(profile, task_id)
            return {
                "taskStatus": response["taskStatus"],
                "videoUrl": response["videoUrl"],
                "taskMessage": self._support.string_value(response.get("taskMessage")),
                "providerResponse": response.get("providerResponse", {}),
                "providerRequest": response.get("providerRequest", {"task_id": task_id}),
                "httpStatus": response.get("httpStatus", 200),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Video task query failed for %s: %s", task_id, exc)
            provider_response = getattr(exc, "provider_response", None)
            return {
                "taskStatus": "UNKNOWN",
                "videoUrl": "",
                "taskMessage": str(exc),
                "providerResponse": provider_response if provider_response is not None else {"error": str(exc)},
                "providerRequest": {"task_id": task_id},
                "httpStatus": getattr(exc, "http_status", 0),
            }

    def _record_query(
        self,
        metadata: dict[str, Any],
        profile: dict[str, Any],
        query: dict[str, Any],
        *,
        success: bool,
    ) -> None:
        interaction = {
            "step": "video.query",
            "providerRequest": query["providerRequest"],
            "providerResponse": query["providerResponse"],
            "httpStatus": query["httpStatus"],
            "endpointHost": profile.get("taskEndpointHost", ""),
            "success": success,
        }
        history = [dict(item) for item in metadata.get("providerQueryHistory", []) if isinstance(item, dict)]
        history.append(interaction)
        metadata["providerQueryHistory"] = history

    def _materialize(
        self, run: dict[str, Any], metadata: dict[str, Any], video_url: str
    ) -> dict[str, Any]:
        relative_dir = self._support.first_non_blank(
            self._support.string_value(metadata.get("storageRelativeDir")),
            f"tasks/_runs/{self._support.string_value(run.get('id'))}",
        )
        file_stem = self._support.first_non_blank(
            self._support.string_value(metadata.get("storageFileStem")), "video"
        )
        return self._support.materialize_binary_artifact(
            self._support.string_value(run.get("id")), relative_dir, file_stem, video_url
        )

    def _error_message(self, message: str, response: object, status: str) -> str:
        return self._support.first_non_blank(
            message,
            self._support.find_nested_string(response, "message", "error", "reason", "detail"),
            status,
        )

    def _append_status_log(
        self,
        call_chain: list[dict[str, Any]],
        event: str,
        status: str,
        task_id: str,
        provider_status: str,
        error: str,
        *,
        output_url: str = "",
    ) -> None:
        payload = {"taskId": task_id, "status": provider_status}
        if error:
            payload["error"] = error
        if output_url:
            payload["outputUrl"] = output_url
        call_chain.append(self._support.call_log("generation", event, status, "", payload))

    def _finish(
        self,
        run: dict[str, Any],
        result: dict[str, Any],
        metadata: dict[str, Any],
        call_chain: list[dict[str, Any]],
        status: str,
    ) -> dict[str, Any]:
        result["callChain"] = call_chain
        result["metadata"] = metadata
        run["result"] = result
        run["resultVideo"] = result
        self._support.update_run_status(run, status)
        return run

    @staticmethod
    def _user_id_from_request(request: dict[str, Any]) -> int | None:
        auth = request.get("auth", {})
        value = auth.get("userId") if isinstance(auth, dict) else None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.strip():
            try:
                return int(value.strip())
            except (TypeError, ValueError):
                return None
        return None

    @classmethod
    def _user_id_from_run(cls, run: dict[str, Any]) -> int | None:
        for source in (run.get("request"), run):
            if isinstance(source, dict):
                user_id = cls._user_id_from_request(source)
                if user_id is not None:
                    return user_id
        for key in ("resultVideo", "result"):
            result = run.get(key)
            metadata = result.get("metadata") if isinstance(result, dict) else None
            if not isinstance(metadata, dict):
                continue
            value = metadata.get("userId")
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str) and value.strip():
                try:
                    return int(value.strip())
                except (TypeError, ValueError):
                    pass
        return None

    @staticmethod
    def _mutable_call_chain(raw: Any) -> list[dict[str, Any]]:
        return [dict(item) for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
