"""HTTP transport and response normalization for task-based video providers."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx

from backend.services.generation_run_factory import GenerationProviderException
from backend.services.model_response_parsing import (
    extract_first_string,
    extract_video_task_id,
    extract_video_task_message,
    extract_video_task_status,
    extract_video_url,
    first_non_blank,
    map_value,
    string_value,
)


class VideoProviderTransport:
    """Send provider requests and normalize task-based API responses."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            follow_redirects=True,
            trust_env=False,
        )

    async def send_json(
        self,
        endpoint: str,
        api_key: str,
        body: dict[str, Any],
        timeout_seconds: int,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        request_payload: dict[str, Any] = {"method": "POST", "url": endpoint, "body": body}
        try:
            response = await self._client.post(
                endpoint,
                headers=headers,
                content=self._encode(body),
                timeout=max(30, timeout_seconds),
            )
        except httpx.RequestError as exc:
            message = str(exc) or exc.__class__.__name__
            raise GenerationProviderException(
                f"provider request failed: {message}", provider_request=request_payload, http_status=0
            ) from exc
        if not 200 <= response.status_code < 300:
            raise GenerationProviderException(
                f"provider request failed: {self._summarize_error_response(response.status_code, response.text)}",
                provider_request=request_payload,
                provider_response=response.text,
                http_status=response.status_code,
            )
        return response

    async def send(self, request: httpx.Request, error_prefix: str) -> httpx.Response:
        request_payload: dict[str, Any] = {"method": request.method, "url": str(request.url)}
        try:
            response = await self._client.send(request)
        except httpx.RequestError as exc:
            raise GenerationProviderException(
                f"{error_prefix}: {exc}", provider_request=request_payload, http_status=0
            ) from exc
        if not 200 <= response.status_code < 300:
            raise GenerationProviderException(
                f"{error_prefix}: {self._summarize_error_response(response.status_code, response.text)}",
                provider_request=request_payload,
                provider_response=response.text,
                http_status=response.status_code,
            )
        return response

    def decode(self, raw: str) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GenerationProviderException(f"provider response decode failed: {exc}") from exc

    def extract_task_id(self, payload: dict[str, Any]) -> str:
        return extract_video_task_id(payload)

    def extract_video_url(self, payload: dict[str, Any]) -> str:
        return extract_video_url(payload)

    def extract_task_status(self, payload: dict[str, Any]) -> str:
        return extract_video_task_status(payload)

    def extract_task_message(self, payload: dict[str, Any]) -> str:
        return extract_video_task_message(payload)

    def encode_path_segment(self, value: str) -> str:
        return quote(value, safe="")

    def extract_first_string(self, raw: object, *keys: str) -> str:
        return extract_first_string(raw, *keys)

    def map_value(self, value: object) -> dict[str, Any]:
        return map_value(value)

    @staticmethod
    def _encode(body: dict[str, Any]) -> str:
        try:
            return json.dumps(body, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise GenerationProviderException(f"provider request encode failed: {exc}") from exc

    @staticmethod
    def _last_resort_body_string(request_payload: dict[str, Any] | None) -> str:
        body = (request_payload or {}).get("body")
        if isinstance(body, str):
            return body
        if isinstance(body, dict):
            return str(body)
        return str(body) if body else ""

    @staticmethod
    def _string_value(value: object) -> str:
        return string_value(value)

    @staticmethod
    def _first_non_blank(*values: str) -> str:
        return first_non_blank(*values)

    @staticmethod
    def _truncate(value: str | None, limit: int) -> str:
        if value is None:
            return ""
        return value if len(value) <= limit else value[:limit]

    @staticmethod
    def _looks_like_html(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return (
            normalized.startswith("<!doctype html")
            or normalized.startswith("<html")
            or "<title>" in normalized
            or "<body" in normalized
        )

    @staticmethod
    def _summarize_error_response(status_code: int, body: str | None) -> str:
        normalized_body = (body or "").strip()
        status_tags = {
            429: "rate limit / quota exceeded",
            402: "payment required / quota exceeded",
            403: "forbidden / permission denied",
            401: "unauthorized / authentication failed",
        }
        status_tag = status_tags.get(status_code)
        if not normalized_body:
            return f"http {status_code}" + (f" {status_tag}" if status_tag else "")
        if VideoProviderTransport._looks_like_html(normalized_body):
            html_summaries = {
                502: "http 502 upstream gateway error",
                503: "http 503 upstream service unavailable",
                504: "http 504 upstream gateway timeout",
            }
            return html_summaries.get(status_code, f"http {status_code} upstream html error page")
        truncated = VideoProviderTransport._truncate(normalized_body, 320)
        if status_tag:
            return f"http {status_code} {status_tag}: {truncated}"
        return f"http {status_code} {truncated}"
