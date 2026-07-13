from types import SimpleNamespace

import pytest

from backend.services.task_video_run_service import TaskVideoRunService


class _GenerationService:
    def __init__(self, runs: list[dict] | None = None) -> None:
        self.runs = list(runs or [])
        self.requested_ids: list[str] = []

    async def get_run(self, run_id: str):  # noqa: ANN201
        self.requested_ids.append(run_id)
        return self.runs.pop(0) if self.runs else None


@pytest.mark.asyncio
async def test_wait_for_run_polls_until_terminal_result() -> None:
    generation_service = _GenerationService([
        {"id": "run-1", "status": "running"},
        {"id": "run-1", "status": "completed", "result": {"outputUrl": "/video.mp4"}},
    ])
    service = TaskVideoRunService(generation_service)

    result = await service.wait_for_run(
        {"id": "run-1", "status": "running"},
        SimpleNamespace(max_polls=2, poll_interval_seconds=0),
    )

    assert result["status"] == "completed"
    assert generation_service.requested_ids == ["run-1", "run-1"]


def test_successful_result_accepts_metadata_output_url() -> None:
    result = TaskVideoRunService.successful_result({
        "id": "run-1",
        "status": "completed",
        "result": {"metadata": {"remoteSourceUrl": "https://provider.test/video.mp4"}},
    })

    assert result["metadata"]["remoteSourceUrl"] == "https://provider.test/video.mp4"


def test_successful_result_reports_provider_failure() -> None:
    with pytest.raises(RuntimeError, match="quota exceeded"):
        TaskVideoRunService.successful_result({
            "id": "run-1",
            "status": "failed",
            "result": {"metadata": {"error": "quota exceeded"}},
        })
