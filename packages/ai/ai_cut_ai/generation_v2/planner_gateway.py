from __future__ import annotations

from typing import Any
import json
import socket
import urllib.error
import urllib.request

from ai_cut_shared.config import RemoteModelTarget, Settings
from ai_cut_shared.utils import (
    build_text_request_body,
    looks_like_qwen_model,
    resolve_llm_request_endpoint,
    should_use_responses_api,
)


class PlannerModelGateway:
    """Adapter used by planners to call remote models via a single boundary."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def invoke_vision(
        self,
        *,
        model_name: str,
        messages: list[dict[str, object]],
        temperature: float,
        max_tokens: int,
    ) -> tuple[dict[str, Any], str]:
        body = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        raw = self._request(
            endpoint=str(self.settings.model.endpoint or "").strip(),
            api_key=str(self.settings.model.api_key or "").strip(),
            body=body,
            timeout_seconds=float(self.settings.model.timeout_seconds),
        )
        return self._parse_raw_json(raw)

    def invoke_text_analysis(
        self,
        *,
        model_name: str,
        target: RemoteModelTarget,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[dict[str, Any], str]:
        use_responses_api = should_use_responses_api(
            provider=target.provider,
            endpoint=target.endpoint,
            model_name=model_name,
        )
        endpoint = resolve_llm_request_endpoint(
            target.endpoint,
            use_responses_api=use_responses_api,
        )
        body = build_text_request_body(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            use_responses_api=use_responses_api,
            enable_thinking=looks_like_qwen_model(model_name),
        )
        raw = self._request(
            endpoint=endpoint,
            api_key=target.api_key,
            body=body,
            timeout_seconds=float(self.settings.model.timeout_seconds),
        )
        return self._parse_raw_json(raw)

    def _request(
        self,
        *,
        endpoint: str,
        api_key: str,
        body: dict[str, Any],
        timeout_seconds: float,
    ) -> bytes:
        if not endpoint:
            raise RuntimeError("model endpoint is empty")
        if not api_key:
            raise RuntimeError("model api key is empty")
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return response.read()
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"model request timed out: {exc}") from exc
        except urllib.error.HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                body_text = ""
            raise RuntimeError(f"model request http error: {exc.code} {body_text[:400]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"model request network error: {exc}") from exc

    def _parse_raw_json(self, raw: bytes) -> tuple[dict[str, Any], str]:
        text = raw.decode("utf-8", errors="ignore")
        try:
            payload = json.loads(text)
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        return payload, text
