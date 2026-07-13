"""HTTP transport for JSON, multipart, and binary image provider operations."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import httpx

from backend.services.generation_run_factory import GenerationProviderException
from backend.services.model_invocation_image_contracts import DownloadedBinary, MultipartFilePart
from backend.services.model_response_parsing import extract_first_string


class ImageProviderTransport:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(120.0), follow_redirects=True, trust_env=False
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
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.post(
                    endpoint, headers=headers, content=self._encode(body), timeout=max(30, timeout_seconds)
                )
            except httpx.RequestError as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
                continue
            if not 200 <= response.status_code < 300:
                if attempt < 2 and response.status_code >= 500:
                    await asyncio.sleep(2**attempt)
                    continue
                raise GenerationProviderException(
                    f"provider request failed: {self._error_summary(response.status_code, response.text)}",
                    provider_request=request_payload,
                    provider_response=response.text,
                    http_status=response.status_code,
                )
            return response
        if last_error is not None:
            message = str(last_error) or last_error.__class__.__name__
            raise GenerationProviderException(
                f"provider request failed: {message}", provider_request=request_payload, http_status=0
            )
        raise GenerationProviderException(
            "provider request failed: all retries exhausted", provider_request=request_payload
        )

    async def download_binary(self, url: str, timeout_seconds: int) -> DownloadedBinary:
        headers = {"User-Agent": "jiandou-python/0.1", "Accept": "*/*"}
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.get(url, headers=headers, timeout=max(15, timeout_seconds))
            except httpx.RequestError as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
                continue
            if not 200 <= response.status_code < 300:
                if attempt < 2 and response.status_code >= 500:
                    await asyncio.sleep(2**attempt)
                    continue
                raise GenerationProviderException(f"remote media download failed: http {response.status_code}")
            return DownloadedBinary(
                data=response.content, mime_type=response.headers.get("content-type", "") or ""
            )
        raise GenerationProviderException(f"remote media download failed: {last_error}")

    async def send_multipart(
        self,
        endpoint: str,
        api_key: str,
        fields: dict[str, str],
        files: list[MultipartFilePart],
        timeout_seconds: int,
        request_payload: dict[str, Any] | None = None,
    ) -> httpx.Response:
        boundary = f"jiandou-{uuid.uuid4().hex}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        }
        payload = request_payload if request_payload is not None else {"method": "POST", "url": endpoint}
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.post(
                    endpoint,
                    headers=headers,
                    content=self._multipart_body(boundary, fields, files),
                    timeout=max(30, timeout_seconds),
                )
            except httpx.RequestError as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
                continue
            if not 200 <= response.status_code < 300:
                if attempt < 2 and response.status_code >= 500:
                    await asyncio.sleep(2**attempt)
                    continue
                raise GenerationProviderException(
                    f"provider multipart request failed: http {response.status_code} {self._truncate(response.text, 320)}",
                    provider_request=payload,
                    provider_response=response.text,
                    http_status=response.status_code,
                )
            return response
        if last_error is not None:
            raise GenerationProviderException(
                f"provider multipart request failed: {last_error}", provider_request=payload, http_status=0
            )
        raise GenerationProviderException(
            "provider multipart request failed: all retries exhausted", provider_request=payload
        )

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
                f"{error_prefix}: {self._error_summary(response.status_code, response.text)}",
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

    def extract_first_string(self, raw: object, *keys: str) -> str:
        return extract_first_string(raw, *keys)

    @staticmethod
    def _encode(body: dict[str, Any]) -> str:
        try:
            return json.dumps(body, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise GenerationProviderException(f"provider request encode failed: {exc}") from exc

    @staticmethod
    def _multipart_body(boundary: str, fields: dict[str, str], files: list[MultipartFilePart]) -> bytes:
        parts: list[bytes] = []
        line_break = "\r\n"
        for name, value in fields.items():
            parts.append(
                f"--{boundary}{line_break}Content-Disposition: form-data; name=\"{name}\"{line_break}"
                f"{line_break}{value}{line_break}".encode()
            )
        for file_part in files:
            parts.append(
                f"--{boundary}{line_break}"
                f"Content-Disposition: form-data; name=\"{file_part.field_name}\"; filename=\"{file_part.file_name}\"{line_break}"
                f"Content-Type: {file_part.content_type or 'application/octet-stream'}{line_break}{line_break}".encode()
            )
            parts.append(file_part.data if file_part.data is not None else b"")
            parts.append(line_break.encode())
        parts.append(f"--{boundary}--{line_break}".encode())
        return b"".join(parts)

    @staticmethod
    def _error_summary(status_code: int, body: str | None) -> str:
        normalized_body = (body or "").strip()
        status_tags = {
            429: "rate limit / quota exceeded",
            402: "payment required / quota exceeded",
            403: "forbidden / permission denied",
            401: "unauthorized / authentication failed",
        }
        tag = status_tags.get(status_code)
        truncated = ImageProviderTransport._truncate(normalized_body, 320) if normalized_body else ""
        if tag:
            return f"http {status_code} {tag}" + (f": {truncated}" if truncated else "")
        return f"http {status_code}" + (f" {truncated}" if truncated else "")

    @staticmethod
    def _truncate(value: str | None, limit: int) -> str:
        if value is None:
            return ""
        return value if len(value) <= limit else value[:limit]
