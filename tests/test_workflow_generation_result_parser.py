from __future__ import annotations

import pytest

pytestmark = pytest.mark.service
import pytest

from backend.services.workflow_generation_result_parser import WorkflowGenerationResultParser


def test_parser_extracts_script_result() -> None:
    parsed = WorkflowGenerationResultParser().parse_script_result({
        "resultScript": {
            "scriptMarkdown": "| 分镜 |",
            "markdownUrl": "/story.md",
            "runId": "run_script",
            "modelInfo": {"model": "text"},
            "callChain": [{"step": "one"}],
        }
    })

    assert parsed.script_markdown == "| 分镜 |"
    assert parsed.output_summary == {
        "scriptMarkdown": "| 分镜 |",
        "markdownUrl": "/story.md",
        "runId": "run_script",
    }
    assert parsed.model_call_summary["modelInfo"] == {"model": "text"}


def test_parser_rejects_empty_script_result() -> None:
    with pytest.raises(ValueError, match="分镜生成失败"):
        WorkflowGenerationResultParser().parse_script_result({"resultScript": {}})


def test_parser_extracts_image_result_with_metadata_fallbacks() -> None:
    parsed = WorkflowGenerationResultParser().parse_image_result(
        {
            "id": "run_image",
            "status": "succeeded",
            "resultImage": {
                "metadata": {
                    "outputUrl": "/image.png",
                    "providerRemoteSourceUrl": "https://provider.example/image.png",
                    "provider": "provider",
                    "providerModel": "image-model",
                },
                "modelInfo": {"model": "image"},
            },
        },
        fallback_width=1280,
        fallback_height=720,
    )

    assert parsed.output_url == "/image.png"
    assert parsed.remote_source_url == "https://provider.example/image.png"
    assert parsed.mime_type == "image/png"
    assert parsed.width == 1280
    assert parsed.height == 720
    assert parsed.run_id == "run_image"
    assert parsed.model_info == {"model": "image"}


def test_parser_rejects_failed_image_result() -> None:
    with pytest.raises(ValueError, match="图片生成失败"):
        WorkflowGenerationResultParser().parse_image_result(
            {"status": "failed", "error": "bad image"},
            fallback_width=1,
            fallback_height=1,
        )


def test_parser_extracts_video_result_with_preview_fallback() -> None:
    parsed = WorkflowGenerationResultParser().parse_video_result(
        {
            "id": "run_video",
            "status": "running",
            "resultVideo": {
                "thumbnailUrl": "/poster.png",
                "metadata": {
                    "taskId": "remote_task",
                    "taskStatus": "SUBMITTED",
                    "provider": "provider",
                    "providerModel": "video-model",
                },
                "modelInfo": {"model": "video"},
            },
        },
        fallback_preview_url="/first.png",
        fallback_width=1280,
        fallback_height=720,
        fallback_duration_seconds=6,
    )

    assert parsed.status == "RUNNING"
    assert parsed.output_url == ""
    assert parsed.preview_url == "/poster.png"
    assert parsed.remote_task_id == "remote_task"
    assert parsed.width == 1280
    assert parsed.height == 720
    assert parsed.duration_seconds == 6.0
    assert parsed.run_id == "run_video"
    assert parsed.model_info == {"model": "video"}


def test_parser_rejects_non_object_video_result() -> None:
    with pytest.raises(ValueError, match="视频生成失败"):
        WorkflowGenerationResultParser().parse_video_result(
            {"resultVideo": None},
            fallback_preview_url="",
            fallback_width=1,
            fallback_height=1,
            fallback_duration_seconds=1,
        )


def test_parser_extracts_video_refresh_result_with_output_fallbacks() -> None:
    parsed = WorkflowGenerationResultParser().parse_video_refresh_result(
        {
            "status": "completed",
            "result": {
                "metadata": {
                    "fileUrl": "/video.mp4",
                    "taskStatus": "FINISHED",
                    "taskId": "remote_task",
                    "remoteSourceUrl": "https://provider.example/video.mp4",
                    "provider": "provider",
                    "providerModel": "video-model",
                },
                "width": "1920",
                "height": "1080",
                "durationSeconds": "7.5",
            },
        },
        output_summary={},
        current_status="RUNNING",
    )

    assert parsed.run_status == "completed"
    assert parsed.output_url == "/video.mp4"
    assert parsed.task_status == "FINISHED"
    assert parsed.remote_task_id == "remote_task"
    assert parsed.remote_source_url == "https://provider.example/video.mp4"
    assert parsed.origin_provider == "provider"
    assert parsed.origin_model == "video-model"
    assert parsed.width == 1920
    assert parsed.height == 1080
    assert parsed.duration_seconds == 7.5


def test_parser_extracts_video_refresh_failure_message() -> None:
    parsed = WorkflowGenerationResultParser().parse_video_refresh_result(
        {
            "status": "failed",
            "resultVideo": {
                "metadata": {
                    "taskMessage": "remote failed",
                },
            },
        },
        output_summary={"taskStatus": "PROCESSING"},
        current_status="RUNNING",
    )

    assert parsed.run_status == "failed"
    assert parsed.output_url == ""
    assert parsed.task_status == "PROCESSING"
    assert parsed.error == "remote failed"


def test_parser_rejects_non_object_video_refresh_result() -> None:
    with pytest.raises(ValueError, match="视频刷新失败"):
        WorkflowGenerationResultParser().parse_video_refresh_result(
            {"resultVideo": "bad"},
            output_summary={},
            current_status="RUNNING",
        )
