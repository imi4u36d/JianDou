"""ASGI middleware that converts all JSON response keys from snake_case to camelCase."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope


def _to_camel(name: str) -> str:
    """Convert snake_case string to camelCase."""
    parts = name.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def _convert_keys(obj: Any) -> Any:
    """Recursively convert all dict keys from snake_case to camelCase."""
    if isinstance(obj, dict):
        return {_to_camel(k): _convert_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_keys(item) for item in obj]
    return obj


class CamelCaseJsonMiddleware:
    """ASGI middleware that converts all JSON response keys to camelCase.

    Works at the ASGI level, BEFORE BaseHTTPMiddleware, so it can
    intercept the raw body and re-encode it with camelCase keys.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Capture the response body sent by the inner app
        body_chunks: list[bytes] = []
        status_code: int = 200
        headers: list[tuple[bytes, bytes]] = []

        async def capturing_send(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                # Capture status and headers but DON'T forward them yet
                status_code = message.get("status", 200)
                headers.extend(message.get("headers", []))
            elif message["type"] == "http.response.body":
                body_chunks.append(message.get("body", b""))

        # Run the inner app with our capturing send
        await self.app(scope, receive, capturing_send)

        # Combine all body chunks
        full_body = b"".join(body_chunks)
        if not full_body:
            # No body — forward headers as-is
            if headers:
                await send({"type": "http.response.start", "status": status_code, "headers": headers})
            return

        # Try to parse as JSON and convert keys
        try:
            data = json.loads(full_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Not JSON — forward as-is
            if headers:
                await send({"type": "http.response.start", "status": status_code, "headers": headers})
            await send({"type": "http.response.body", "body": full_body})
            return

        converted = _convert_keys(data)
        converted_body = json.dumps(converted, ensure_ascii=False).encode("utf-8")

        # Recalculate Content-Length header
        new_headers = []
        for name, value in headers:
            if name == b"content-length":
                new_headers.append((name, str(len(converted_body)).encode()))
            else:
                new_headers.append((name, value))

        # Send the converted response
        await send({"type": "http.response.start", "status": status_code, "headers": new_headers})
        await send(
            {
                "type": "http.response.body",
                "body": converted_body,
            }
        )
