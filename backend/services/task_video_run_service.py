"""Generation-run polling and result validation for task video stages."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.domain.generation_run import GenerationRunStatuses
from backend.shared import first_non_blank, map_value, string_value


class TaskVideoRunService:
    def __init__(self, generation_application_service: Any) -> None:
        self._generation_application_service = generation_application_service

    async def wait_for_run(self, video_run: dict[str, Any], options: Any) -> dict[str, Any]:
        current = dict(video_run or {})
        run_id = string_value(current.get("id"))
        for attempt in range(max(0, options.max_polls) + 1):
            status = string_value(current.get("status")).lower()
            if not GenerationRunStatuses.is_active(status):
                return current
            if attempt >= max(0, options.max_polls):
                break
            if options.poll_interval_seconds > 0:
                await asyncio.sleep(options.poll_interval_seconds)
            getter = getattr(self._generation_application_service, "get_run", None)
            if not callable(getter):
                break
            refreshed = await getter(run_id)
            if refreshed:
                current = dict(refreshed)
        raise RuntimeError(f"video run {run_id} did not finish within polling limit")

    async def get_run(self, run_id: str) -> dict[str, Any]:
        getter = getattr(self._generation_application_service, "get_run", None)
        if not callable(getter):
            raise RuntimeError("generation service does not support run lookup")
        run = await getter(run_id)
        if not run:
            raise RuntimeError(f"video run {run_id} was not found")
        return dict(run)

    @staticmethod
    def successful_result(video_run: dict[str, Any]) -> dict[str, Any]:
        status = string_value(video_run.get("status")).lower()
        result = map_value(video_run.get("result"))
        metadata = map_value(result.get("metadata"))
        if not GenerationRunStatuses.is_successful(status):
            error = first_non_blank(
                string_value(result.get("error")),
                string_value(metadata.get("error")),
                string_value(video_run.get("error")),
                status,
            )
            raise RuntimeError(f"video run failed: {error}")
        output_url = first_non_blank(
            string_value(result.get("outputUrl")),
            string_value(metadata.get("outputUrl")),
            string_value(metadata.get("fileUrl")),
            string_value(metadata.get("remoteSourceUrl")),
        )
        if not output_url:
            raise RuntimeError("video run succeeded without output url")
        return result
