from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _trim(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback.strip()
    stripped = str(value).strip()
    return stripped if stripped else fallback.strip()


def _safe_int(value: Any, fallback: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if value is not None:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if value is not None:
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            pass
    return fallback


@dataclass(frozen=True)
class ParsedScriptResult:
    script_markdown: str
    output_summary: dict[str, Any]
    model_call_summary: dict[str, Any]


@dataclass(frozen=True)
class ParsedImageResult:
    raw: dict[str, Any]
    metadata: dict[str, Any]
    output_url: str
    remote_source_url: str
    mime_type: str
    width: int
    height: int
    run_id: str
    model_info: dict[str, Any]


@dataclass(frozen=True)
class ParsedVideoResult:
    raw: dict[str, Any]
    metadata: dict[str, Any]
    status: str
    output_url: str
    remote_task_id: str
    preview_url: str
    mime_type: str
    width: int
    height: int
    duration_seconds: float
    run_id: str
    model_info: dict[str, Any]


@dataclass(frozen=True)
class ParsedVideoRefreshResult:
    raw: dict[str, Any]
    metadata: dict[str, Any]
    run_status: str
    output_url: str
    task_status: str
    error: str
    mime_type: str
    width: int
    height: int
    duration_seconds: float
    remote_task_id: str
    remote_source_url: str
    origin_provider: str
    origin_model: str


class WorkflowGenerationResultParser:
    """Parse generation-service responses for workflow stages."""

    def parse_script_result(self, gen_result: dict[str, Any]) -> ParsedScriptResult:
        result_script = gen_result.get("resultScript", gen_result.get("result", {}))
        script_markdown = ""
        output_summary: dict[str, Any] = {}
        model_call_summary: dict[str, Any] = {}
        if isinstance(result_script, dict):
            script_markdown = _trim(result_script.get("scriptMarkdown"))
            output_summary = {
                "scriptMarkdown": script_markdown,
                "markdownUrl": result_script.get("markdownUrl", ""),
                "runId": result_script.get("runId", ""),
            }
            model_call_summary = {
                "modelInfo": result_script.get("modelInfo", {}),
                "callChain": result_script.get("callChain", []),
            }
        if not script_markdown:
            raise ValueError("分镜生成失败：模型返回为空，请重试。")
        return ParsedScriptResult(
            script_markdown=script_markdown,
            output_summary=output_summary,
            model_call_summary=model_call_summary,
        )

    def parse_image_result(
        self,
        gen_result: dict[str, Any],
        *,
        fallback_width: int,
        fallback_height: int,
    ) -> ParsedImageResult:
        image_result = gen_result.get("resultImage", gen_result.get("result", {}))
        if gen_result.get("status") not in ("succeeded", "completed", "success") or not isinstance(image_result, dict):
            raise ValueError(f"图片生成失败：{gen_result.get('error') or '模型返回为空'}")
        metadata = image_result.get("metadata", {}) if isinstance(image_result.get("metadata"), dict) else {}
        output_url = _trim(image_result.get("outputUrl") or metadata.get("outputUrl"))
        if not output_url:
            raise ValueError("图片生成失败：模型未返回图片。")
        remote_source_url = _first_non_blank(
            _trim(metadata.get("remoteSourceUrl")),
            _trim(metadata.get("providerRemoteSourceUrl")),
            _trim(image_result.get("remoteSourceUrl")),
        )
        return ParsedImageResult(
            raw=image_result,
            metadata=metadata,
            output_url=output_url,
            remote_source_url=remote_source_url,
            mime_type=_trim(image_result.get("mimeType"), "image/png"),
            width=_safe_int(image_result.get("width"), fallback_width),
            height=_safe_int(image_result.get("height"), fallback_height),
            run_id=_trim(image_result.get("runId") or gen_result.get("id", "")),
            model_info=image_result.get("modelInfo", {}) if isinstance(image_result.get("modelInfo"), dict) else {},
        )

    def parse_video_result(
        self,
        gen_result: dict[str, Any],
        *,
        fallback_preview_url: str,
        fallback_width: int,
        fallback_height: int,
        fallback_duration_seconds: int,
    ) -> ParsedVideoResult:
        video_result = gen_result.get("resultVideo", gen_result.get("result", {}))
        if not isinstance(video_result, dict):
            raise ValueError(f"视频生成失败：{gen_result.get('error') or '模型返回为空'}")
        metadata = video_result.get("metadata", {}) if isinstance(video_result.get("metadata"), dict) else {}
        status = _trim(gen_result.get("status"), "running").upper()
        output_url = _trim(video_result.get("outputUrl") or metadata.get("outputUrl"))
        remote_task_id = _trim(metadata.get("taskId"))
        preview_url = output_url or _trim(video_result.get("thumbnailUrl")) or fallback_preview_url
        return ParsedVideoResult(
            raw=video_result,
            metadata=metadata,
            status=status,
            output_url=output_url,
            remote_task_id=remote_task_id,
            preview_url=preview_url,
            mime_type=_trim(video_result.get("mimeType"), "video/mp4"),
            width=_safe_int(video_result.get("width"), fallback_width),
            height=_safe_int(video_result.get("height"), fallback_height),
            duration_seconds=_safe_float(video_result.get("durationSeconds"), float(fallback_duration_seconds)),
            run_id=_trim(video_result.get("runId") or gen_result.get("id", "")),
            model_info=video_result.get("modelInfo", {}) if isinstance(video_result.get("modelInfo"), dict) else {},
        )

    def parse_video_refresh_result(
        self,
        run: dict[str, Any],
        *,
        output_summary: dict[str, Any],
        current_status: str,
    ) -> ParsedVideoRefreshResult:
        video_result = run.get("resultVideo") or run.get("result") or {}
        if not isinstance(video_result, dict):
            raise ValueError("视频刷新失败：模型返回为空。")
        metadata = video_result.get("metadata", {}) if isinstance(video_result.get("metadata"), dict) else {}
        return ParsedVideoRefreshResult(
            raw=video_result,
            metadata=metadata,
            run_status=_trim(run.get("status")).lower(),
            output_url=_trim(video_result.get("outputUrl") or metadata.get("outputUrl") or metadata.get("fileUrl")),
            task_status=_trim(metadata.get("taskStatus") or output_summary.get("taskStatus") or current_status),
            error=_trim(video_result.get("error") or metadata.get("taskMessage") or metadata.get("error")),
            mime_type=_trim(video_result.get("mimeType"), "video/mp4"),
            width=_safe_int(video_result.get("width") or output_summary.get("width"), 0),
            height=_safe_int(video_result.get("height") or output_summary.get("height"), 0),
            duration_seconds=_safe_float(
                video_result.get("durationSeconds") or output_summary.get("durationSeconds"),
                0.0,
            ),
            remote_task_id=_trim(metadata.get("taskId") or output_summary.get("taskId")),
            remote_source_url=_trim(metadata.get("remoteSourceUrl")),
            origin_provider=_trim(metadata.get("provider")),
            origin_model=_trim(metadata.get("providerModel")),
        )


def _first_non_blank(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""
