"""Shared helpers for building and persisting generation run results."""

from __future__ import annotations

from typing import Any

from backend.config import settings
from backend.domain.generation_run import GenerationRunStatuses
from backend.services.generation_artifacts import GenerationArtifactStore, extension_from_mime_or_url
from backend.services.generation_payloads import (
    append_negative_prompt,
    build_media_model_info,
    build_model_info,
    infer_camera_fixed,
)
from backend.services.generation_request_values import (
    find_nested_string,
    map_value,
    nested_boolean,
    nested_int,
    nested_nullable_int,
    nested_string_list,
    nested_value,
    string_list,
    string_value,
)
from backend.shared import first_non_blank, first_positive_int, now_iso, positive_int, truncate_text


class GenerationRunSupport:
    """Utility methods shared by generation run orchestration services."""

    def __init__(self) -> None:
        self._storage_root: str = getattr(settings, "storage_root", "./storage")
        from backend.services.object_storage import create_remote_object_storage

        self._artifact_store = GenerationArtifactStore(
            self._storage_root,
            getattr(settings, "web_origin", "http://127.0.0.1:80"),
            create_remote_object_storage(settings),
        )

    def run_envelope(
        self,
        run_id: str,
        kind: str,
        request: dict[str, Any],
        result: dict[str, Any],
        specific_result_key: str,
        status: str = GenerationRunStatuses.SUCCEEDED,
    ) -> dict[str, Any]:
        now = self.now_iso()
        return {
            "id": run_id,
            "kind": kind,
            "status": status,
            "createdAt": now,
            "updatedAt": now,
            "input": self.map_value(request.get("input")),
            "model": self.map_value(request.get("model")),
            "options": self.map_value(request.get("options")),
            "storage": self.map_value(request.get("storage")),
            "auth": self.map_value(request.get("auth")),
            "result": result,
            specific_result_key: result,
        }

    def update_run_status(self, run: dict[str, Any], status: str) -> None:
        run["status"] = status
        run["updatedAt"] = self.now_iso()

    def nested_value(self, payload: dict[str, Any], parent_key: str, child_key: str, default: str = "") -> str:
        return nested_value(payload, parent_key, child_key, default)

    def nested_string_list(self, payload: dict[str, Any], parent_key: str, child_key: str) -> list[str]:
        return nested_string_list(payload, parent_key, child_key)

    def nested_int(self, payload: dict[str, Any], parent_key: str, child_key: str, default: int = 0) -> int:
        return nested_int(payload, parent_key, child_key, default)

    def nested_nullable_int(self, payload: dict[str, Any], parent_key: str, child_key: str) -> int | None:
        return nested_nullable_int(payload, parent_key, child_key)

    def nested_boolean(self, payload: dict[str, Any], parent_key: str, child_key: str, default: bool = False) -> bool:
        return nested_boolean(payload, parent_key, child_key, default)

    def map_value(self, value: Any) -> dict[str, Any]:
        return map_value(value)

    def string_value(self, value: Any) -> str:
        return string_value(value)

    def first_non_blank(self, *values: str) -> str:
        return first_non_blank(*values)

    def find_nested_string(self, value: Any, *keys: str) -> str:
        return find_nested_string(value, *keys)

    def required_model(self, value: str, field_name: str, label: str) -> str:
        normalized = value.strip() if value else ""
        if normalized:
            return normalized
        raise ValueError(f"请先选择{label}（{field_name}）")

    def now_iso(self) -> str:
        return now_iso()

    def truncate_text(self, value: str, limit: int) -> str:
        return truncate_text(value, limit)

    @staticmethod
    def strip_markdown_fence(text: str) -> str:
        value = text.strip() if text else ""
        if not value.startswith("```"):
            return value
        first_break = value.find("\n")
        last_fence = value.rfind("```")
        if first_break < 0 or last_fence <= first_break:
            return value.replace("```", "").strip()
        return value[first_break + 1 : last_fence].strip()

    @staticmethod
    def bounded_temperature(value: float, min_val: float, max_val: float) -> float:
        return max(min_val, min(max_val, value))

    def positive_int(self, raw: str, fallback: int) -> int:
        return positive_int(raw, fallback)

    def first_positive_int(self, *values: int) -> int:
        return first_positive_int(*values)

    @staticmethod
    def normalize_value(value: str) -> str:
        return value.strip().lower() if value else ""

    def normalize_frame_role(self, frame_role: str) -> str:
        return "last" if self.string_value(frame_role).lower() == "last" else "first"

    @staticmethod
    def parse_dimensions(raw: str, fallback_width: int, fallback_height: int) -> tuple[int, int]:
        normalized = raw.strip().lower().replace("x", "*") if raw else ""
        parts = normalized.split("*")
        if len(parts) == 2:
            try:
                return int(parts[0]), int(parts[1])
            except (ValueError, TypeError):
                pass
        return fallback_width, fallback_height

    @staticmethod
    def extension_from_mime_or_url(mime_type: str, source_url: str, media_type: str) -> str:
        return extension_from_mime_or_url(mime_type, source_url, media_type)

    @staticmethod
    def append_negative_prompt(prompt: str, negative_prompt: str) -> str:
        return append_negative_prompt(prompt, negative_prompt)

    @staticmethod
    def infer_camera_fixed(prompt: str, fallback: bool) -> bool:
        return infer_camera_fixed(prompt, fallback)

    def storage_relative_dir(self, request: dict[str, Any], run_id: str) -> str:
        return self._artifact_store.storage_relative_dir(request, run_id)

    def storage_file_stem(self, request: dict[str, Any], fallback: str) -> str:
        return self._artifact_store.storage_file_stem(request, fallback)

    def storage_file_name(self, request: dict[str, Any], fallback: str) -> str:
        return self._artifact_store.storage_file_name(request, fallback)

    @staticmethod
    def string_list(value: Any) -> list[str]:
        return string_list(value)

    def integer_list(self, value: Any) -> list[int]:
        if not isinstance(value, list):
            return []
        result: list[int] = []
        for item in value:
            parsed = self.positive_int(str(item) if item is not None else "", 0)
            if parsed > 0:
                result.append(parsed)
        return result

    @staticmethod
    def parse_string_list(raw: str, fallback: list[str]) -> list[str]:
        items = [part.strip() for part in raw.split(",") if part and part.strip()] if raw else []
        return items or fallback

    def parse_integer_list(self, raw: str, fallback: list[int]) -> list[int]:
        parsed = [self.positive_int(part, 0) for part in raw.split(",") if part and part.strip()] if raw else []
        items = [item for item in parsed if item > 0]
        return items or fallback

    def call_log(
        self, stage: str, event: str, status: str, message: str, details: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        safe = {key: value for key, value in (details or {}).items() if value is not None}
        safe.setdefault("source", "python")
        return {
            "timestamp": self.now_iso(),
            "stage": stage,
            "event": event,
            "status": status,
            "message": message,
            "details": safe,
        }

    @staticmethod
    def build_model_info(
        profile: dict[str, Any],
        requested_model: str,
        media_kind: str,
        response: dict[str, Any] | None,
        source_tag: str,
    ) -> dict[str, Any]:
        return build_model_info(profile, requested_model, media_kind, response, source_tag)

    @staticmethod
    def build_media_model_info(
        text_profile: dict[str, Any],
        rewrite_profile: dict[str, Any] | None,
        vision_profile: dict[str, Any] | None,
        media_profile: dict[str, Any],
        requested_model: str,
        media_kind: str,
        text_response: dict[str, Any] | None,
        vision_response: dict[str, Any] | None,
        resolved_model: str,
        endpoint_host: str,
        task_endpoint_host: str,
        source_tag: str,
    ) -> dict[str, Any]:
        return build_media_model_info(
            text_profile,
            rewrite_profile,
            vision_profile,
            media_profile,
            requested_model,
            media_kind,
            text_response,
            vision_response,
            resolved_model,
            endpoint_host,
            task_endpoint_host,
            source_tag,
        )

    def write_text_artifact(
        self, run_id: str, request: dict[str, Any], file_name: str, content: str
    ) -> dict[str, Any]:
        return self._artifact_store.write_text_artifact(run_id, request, file_name, content)

    def write_binary_artifact(
        self,
        run_id: str,
        request: dict[str, Any],
        file_stem: str,
        extension: str,
        data: bytes,
    ) -> dict[str, Any]:
        return self._artifact_store.write_binary_artifact(run_id, request, file_stem, extension, data)

    def materialize_binary_artifact(
        self, run_id: str, relative_dir: str, file_stem: str, source_url: str
    ) -> dict[str, Any]:
        return self._artifact_store.materialize_binary_artifact(run_id, relative_dir, file_stem, source_url)

    def build_externally_accessible_url(self, public_url: str) -> str:
        return self._artifact_store.build_externally_accessible_url(public_url)

    def image_data_uri_from_public_url(self, public_url: str) -> str:
        return self._artifact_store.image_data_uri_from_public_url(public_url)
