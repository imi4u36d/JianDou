"""HTTP and SSE transport for OpenAI-compatible text providers."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlparse

import httpx

from backend.services.generation_run_factory import GenerationProviderException
from backend.services.model_response_parsing import extract_text_response, string_value


class TextProviderTransport:
    """Encode, send, and decode OpenAI-compatible text requests."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(120.0), trust_env=False)

    async def send_json(
        self,
        endpoint: str,
        api_key: str,
        body: dict[str, Any],
        timeout_seconds: int,
        error_prefix: str,
    ) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        timeout = max(30, timeout_seconds)
        raw_body = self._encode(body)
        try:
            response = await self._client.post(
                endpoint,
                headers=headers,
                content=raw_body,
                timeout=timeout,
            )
        except httpx.RequestError as ex:
            raise GenerationProviderException(
                f"{error_prefix}: {ex}",
                provider_request={"method": "POST", "url": endpoint, "body": body},
                http_status=0,
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise GenerationProviderException(
                f"{error_prefix}: http {response.status_code} {self._truncate(response.text, 320)}",
                provider_request={"method": "POST", "url": endpoint, "body": body},
                provider_response=response.text,
                http_status=response.status_code,
            )
        return response

    async def send_streaming_json(
        self,
        endpoint: str,
        api_key: str,
        body: dict[str, Any],
        timeout_seconds: int,
        error_prefix: str,
    ) -> tuple[dict[str, Any], int]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
        }
        timeout = max(30, timeout_seconds)
        raw_body = self._encode(body)
        try:
            async with self._client.stream(
                "POST",
                endpoint,
                headers=headers,
                content=raw_body,
                timeout=timeout,
            ) as response:
                try:
                    raw_bytes = await asyncio.wait_for(response.aread(), timeout=timeout)
                except TimeoutError:
                    raise GenerationProviderException(
                        f"{error_prefix}: stream response timed out after {timeout}s",
                        provider_request={"method": "POST", "url": endpoint, "body": body},
                        http_status=response.status_code,
                    )
                raw = raw_bytes.decode("utf-8", errors="replace")
                if response.status_code < 200 or response.status_code >= 300:
                    raise GenerationProviderException(
                        f"{error_prefix}: http {response.status_code} {self._truncate(raw, 320)}",
                        provider_request={"method": "POST", "url": endpoint, "body": body},
                        provider_response=raw,
                        http_status=response.status_code,
                    )
                payload = self.decode_stream(raw)
                stream_error = self.stream_error_message(payload)
                if stream_error:
                    raise GenerationProviderException(
                        f"{error_prefix}: {stream_error}",
                        provider_request={"method": "POST", "url": endpoint, "body": body},
                        provider_response=payload,
                        http_status=response.status_code,
                    )
                if self.stream_response_empty(payload):
                    raise GenerationProviderException(
                        f"{error_prefix}: stream response did not include text or events",
                        provider_request={"method": "POST", "url": endpoint, "body": body},
                        provider_response=raw,
                        http_status=response.status_code,
                    )
                return payload, response.status_code
        except httpx.RequestError as ex:
            raise GenerationProviderException(
                f"{error_prefix}: {ex}",
                provider_request={"method": "POST", "url": endpoint, "body": body},
                http_status=0,
            )

    async def send(self, request: httpx.Request, error_prefix: str) -> httpx.Response:
        request_payload: dict[str, Any] = {"method": request.method, "url": str(request.url)}
        return await self._send_raw(request, error_prefix, request_payload)

    async def _send_raw(
        self,
        request: httpx.Request,
        error_prefix: str,
        request_payload: dict[str, Any],
    ) -> httpx.Response:
        try:
            response = await self._client.send(request)
        except httpx.RequestError as ex:
            raise GenerationProviderException(
                f"{error_prefix}: {ex}", provider_request=request_payload, http_status=0
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise GenerationProviderException(
                f"{error_prefix}: http {response.status_code} {self._truncate(response.text, 320)}",
                provider_request=request_payload,
                provider_response=response.text,
                http_status=response.status_code,
            )
        return response

    def decode(self, raw: str) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as ex:
            raise GenerationProviderException(f"text model response decode failed: {ex}")

    def decode_stream(self, raw: str) -> dict[str, Any]:
        stripped = (raw or "").strip()
        if not stripped:
            return {}
        if stripped.startswith("{"):
            return self.decode(stripped)

        parts: list[str] = []
        events: list[dict[str, Any]] = []
        final_response: dict[str, Any] = {}
        response_id = ""
        for line in stripped.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            events.append(event)
            if not response_id:
                response_id = string_value(event.get("id"))
            self._append_stream_event_text(parts, event)
            nested_response = event.get("response")
            if isinstance(nested_response, dict):
                final_response = nested_response

        text = "".join(parts).strip()
        if final_response:
            final_response = dict(final_response)
            if text and not string_value(final_response.get("output_text")):
                final_response["output_text"] = text
            final_response.setdefault("stream_events", events)
            return final_response
        return {"id": response_id, "output_text": text, "stream_events": events}

    def stream_error_message(self, payload: dict[str, Any]) -> str:
        error = payload.get("error")
        if isinstance(error, dict):
            return self._format_stream_error(error)
        status = string_value(payload.get("status")).lower()
        if status == "failed":
            return self._format_stream_error(payload.get("error")) or "stream response failed"
        events = payload.get("stream_events")
        if isinstance(events, list):
            for event in events:
                if not isinstance(event, dict):
                    continue
                event_error = event.get("error")
                if isinstance(event_error, dict):
                    return self._format_stream_error(event_error)
                nested_response = event.get("response")
                if isinstance(nested_response, dict):
                    nested_status = string_value(nested_response.get("status")).lower()
                    if nested_status == "failed":
                        return (
                            self._format_stream_error(nested_response.get("error"))
                            or "stream response failed"
                        )
        return ""

    def stream_response_empty(self, payload: dict[str, Any]) -> bool:
        if string_value(payload.get("output_text")):
            return False
        if payload.get("choices") or payload.get("output"):
            return False
        events = payload.get("stream_events")
        return isinstance(events, list) and not events

    @staticmethod
    def _format_stream_error(error: object) -> str:
        if isinstance(error, dict):
            message = string_value(error.get("message"))
            code = string_value(error.get("code") or error.get("type"))
            if message and code:
                return f"{code}: {message}"
            return message or code
        return string_value(error)

    def _append_stream_event_text(self, parts: list[str], event: dict[str, Any]) -> None:
        event_type = string_value(event.get("type"))
        if event_type in ("response.output_text.delta", "response.refusal.delta"):
            parts.append(string_value(event.get("delta")))
            return
        if event_type in ("response.output_text.done", "response.completed"):
            return

        choices = event.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                delta = choice.get("delta")
                if isinstance(delta, dict):
                    content = delta.get("content")
                    if isinstance(content, str):
                        parts.append(content)
                    elif isinstance(content, list):
                        self._append_content_text(parts, content)
                message = choice.get("message")
                if isinstance(message, dict):
                    self._append_content_text(parts, message.get("content"))

    def _append_content_text(self, parts: list[str], raw: object) -> None:
        if isinstance(raw, str):
            parts.append(raw)
            return
        if isinstance(raw, list):
            for item in raw:
                self._append_content_text(parts, item)
            return
        if isinstance(raw, dict):
            self._append_content_text(parts, raw.get("text") or raw.get("content"))

    def extract_text(self, response_map: dict[str, Any]) -> str:
        return extract_text_response(response_map)

    def endpoint_host(self, endpoint: str) -> str:
        try:
            host = urlparse(endpoint).hostname
            return host or ""
        except Exception:
            return ""

    def string_value(self, value: object) -> str:
        return string_value(value)

    def _encode(self, body: dict[str, Any]) -> str:
        try:
            return json.dumps(body, ensure_ascii=False)
        except (TypeError, ValueError) as ex:
            raise GenerationProviderException(f"text model request encode failed: {ex}")

    @staticmethod
    def _truncate(value: str | None, limit: int) -> str:
        if value is None:
            return ""
        return value if len(value) <= limit else value[:limit]
