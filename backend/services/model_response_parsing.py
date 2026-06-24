from __future__ import annotations

from typing import Any

VIDEO_URL_KEYS = ("video_url", "videoUrl", "url", "file_url", "fileUrl", "media_url", "mediaUrl", "remixed_from_video_id", "remixedFromVideoId")
TASK_STATUS_KEYS = ("task_status", "taskStatus", "status", "state")
TASK_MESSAGE_KEYS = ("message", "error")


def string_value(value: object) -> str:
    return "" if value is None else str(value).strip()


def first_non_blank(*values: str) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def map_value(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return {}


def extract_first_string(raw: object, *keys: str) -> str:
    if isinstance(raw, dict):
        for key in keys:
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, (dict, list)):
                nested = extract_first_string(value, *keys)
                if nested:
                    return nested
        for value in raw.values():
            nested = extract_first_string(value, *keys)
            if nested:
                return nested
    if isinstance(raw, list):
        for item in raw:
            nested = extract_first_string(item, *keys)
            if nested:
                return nested
    return ""


def extract_text_response(response_map: dict[str, Any]) -> str:
    output_text = string_value(response_map.get("output_text"))
    if output_text:
        return output_text
    from_output_object = _extract_text_from_output_object(response_map.get("output"))
    if from_output_object:
        return from_output_object
    from_output = _extract_text_from_output(response_map.get("output"))
    if from_output:
        return from_output
    from_choices = _extract_text_from_choices(response_map.get("choices"))
    if from_choices:
        return from_choices
    from_message = _extract_text_from_message(response_map.get("message"))
    if from_message:
        return from_message
    return string_value(response_map.get("text"))


def extract_video_task_id(payload: dict[str, Any]) -> str:
    return first_non_blank(
        string_value(payload.get("task_id")),
        string_value(payload.get("taskId")),
        string_value(payload.get("id")),
        string_value(map_value(payload.get("output")).get("task_id")),
        string_value(map_value(payload.get("output")).get("taskId")),
        string_value(map_value(payload.get("data")).get("task_id")),
        string_value(map_value(payload.get("data")).get("taskId")),
    )


def extract_video_url(payload: dict[str, Any]) -> str:
    return extract_first_string(payload, *VIDEO_URL_KEYS)


def extract_video_task_status(payload: dict[str, Any]) -> str:
    status = first_non_blank(
        extract_first_string(payload, *TASK_STATUS_KEYS),
        extract_first_string(map_value(payload.get("output")), *TASK_STATUS_KEYS),
        extract_first_string(map_value(payload.get("data")), *TASK_STATUS_KEYS),
        "UNKNOWN",
    )
    return status.upper()


def extract_video_task_message(payload: dict[str, Any]) -> str:
    return first_non_blank(
        extract_first_string(payload, *TASK_MESSAGE_KEYS),
        extract_first_string(map_value(payload.get("output")), *TASK_MESSAGE_KEYS),
        extract_first_string(map_value(payload.get("data")), *TASK_MESSAGE_KEYS),
    )


def _extract_text_from_output(raw: object) -> str:
    if not isinstance(raw, list):
        return ""
    parts: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            _append_content(parts, item.get("content"))
    return "".join(parts).strip()


def _extract_text_from_output_object(raw: object) -> str:
    if not isinstance(raw, dict):
        return ""
    text = string_value(raw.get("text"))
    if text:
        return text
    from_choices = _extract_text_from_choices(raw.get("choices"))
    if from_choices:
        return from_choices
    from_message = _extract_text_from_message(raw.get("message"))
    if from_message:
        return from_message
    parts: list[str] = []
    _append_content(parts, raw.get("content"))
    return "".join(parts).strip()


def _extract_text_from_choices(raw: object) -> str:
    if not isinstance(raw, list) or not raw:
        return ""
    first = raw[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        parts: list[str] = []
        _append_content(parts, content)
        return "".join(parts).strip()
    return string_value(first.get("text"))


def _extract_text_from_message(raw: object) -> str:
    if not isinstance(raw, dict):
        return ""
    content = raw.get("content")
    if isinstance(content, str):
        return content.strip()
    parts: list[str] = []
    _append_content(parts, content)
    return "".join(parts).strip()


def _append_content(parts: list[str], raw: object) -> None:
    if isinstance(raw, str):
        text = raw.strip()
        if text:
            if parts:
                parts.append("\n")
            parts.append(text)
        return
    if isinstance(raw, list):
        for item in raw:
            _append_content(parts, item)
        return
    if not isinstance(raw, dict):
        return
    entry_type = raw.get("type")
    if entry_type in ("output_text", "text"):
        _append_content(parts, raw.get("text"))
        return
    if entry_type == "message":
        _append_content(parts, raw.get("content"))
        return
    if "content" in raw:
        _append_content(parts, raw.get("content"))

