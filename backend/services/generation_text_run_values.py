"""Pure request and provider-response projections for text generation runs."""

from __future__ import annotations

from typing import Any


def user_id_from_request(request: dict[str, Any]) -> int | None:
    auth = request.get("auth", {})
    if not isinstance(auth, dict):
        return None
    user_id = auth.get("userId")
    if isinstance(user_id, (int, float)):
        return int(user_id)
    if isinstance(user_id, str) and user_id.strip():
        try:
            return int(user_id.strip())
        except (ValueError, TypeError):
            pass
    return None


def request_metadata(request: dict[str, Any]) -> dict[str, Any]:
    metadata = request.get("metadata") if request else None
    return metadata if isinstance(metadata, dict) else {}


def invalid_storyboard_reason(storyboard: str) -> str:
    if not storyboard or not storyboard.strip():
        return "review output is blank"
    has_material_section = any(
        marker in storyboard
        for marker in ("【公共素材定义】", "【角色定义信息】", "【 角色 】", "【 】")
    )
    if not has_material_section:
        return "review output missing public material definitions"
    if not any(marker in storyboard for marker in ("【分镜脚本】", "【 分镜 】", "【 】")):
        return "review output missing storyboard section"
    return ""


def text_provider_interaction(step: str, response: dict[str, Any]) -> dict[str, Any]:
    http_status = response.get("httpStatus", 0)
    return {
        "step": step,
        "providerRequest": response.get("providerRequest", {}),
        "providerResponse": response.get("providerResponse", {}),
        "httpStatus": http_status,
        "endpointHost": response.get("endpointHost", ""),
        "success": http_status == 0 or 200 <= http_status < 300,
        "responseId": response.get("responseId", ""),
        "responsesApi": response.get("responsesApi", False),
        "latencyMs": response.get("latencyMs", 0),
    }
