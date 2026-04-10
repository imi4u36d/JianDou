from __future__ import annotations

from typing import Any
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from ai_cut_shared.config import Settings

from .base import ProviderResult, ResolvedModelTarget


def _llm_api_base(endpoint: str) -> str:
    normalized = str(endpoint or "").strip().rstrip("/")
    if not normalized:
        return ""
    for suffix in ("/chat/completions", "/responses"):
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def _should_use_responses_api(target: ResolvedModelTarget) -> bool:
    extras = target.extras
    explicit = extras.get("use_responses_api")
    if isinstance(explicit, bool):
        return explicit
    endpoint = str(target.base_url or "").strip().rstrip("/")
    if endpoint.endswith("/responses"):
        return True
    if endpoint.endswith("/chat/completions"):
        return False
    parsed = urllib.parse.urlparse(endpoint)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower().rstrip("/")
    if host.endswith("dashscope.aliyuncs.com"):
        return True
    return path.endswith("/v1")


def _resolve_request_endpoint(target: ResolvedModelTarget, use_responses_api: bool) -> str:
    base = _llm_api_base(target.base_url)
    if not base:
        return ""
    return f"{base}/responses" if use_responses_api else f"{base}/chat/completions"


def _build_text_request_body(
    *,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    use_responses_api: bool,
    enable_thinking: bool,
) -> dict[str, Any]:
    if use_responses_api:
        body: dict[str, Any] = {
            "model": model_name,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if enable_thinking:
            body["enable_thinking"] = True
        return body
    return {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


class OpenAICompatibleAdapter:
    name = "openai_compatible"

    def invoke_text(
        self,
        *,
        settings: Settings,
        target: ResolvedModelTarget,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        enable_thinking: bool = False,
        file_input_path=None,
        file_input_name=None,
    ) -> ProviderResult:
        use_responses_api = _should_use_responses_api(target)
        endpoint = _resolve_request_endpoint(target, use_responses_api=use_responses_api)
        body = _build_text_request_body(
            model_name=target.model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            use_responses_api=use_responses_api,
            enable_thinking=enable_thinking,
        )
        payload, raw = self._request_json(
            endpoint=endpoint,
            api_key=target.api_key,
            body=body,
            timeout_seconds=float(settings.model.timeout_seconds),
        )
        return ProviderResult(
            payload=payload,
            raw_text=raw,
            endpoint=endpoint,
            mode="responses_key" if use_responses_api else "chat_completions",
        )

    def invoke_vision(
        self,
        *,
        settings: Settings,
        target: ResolvedModelTarget,
        messages: list[dict[str, object]],
        temperature: float,
        max_tokens: int,
    ) -> ProviderResult:
        endpoint = str(target.base_url or "").strip()
        body = {
            "model": target.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        payload, raw = self._request_json(
            endpoint=endpoint,
            api_key=target.api_key,
            body=body,
            timeout_seconds=float(settings.model.timeout_seconds),
        )
        return ProviderResult(payload=payload, raw_text=raw, endpoint=endpoint, mode="vision_messages")

    def _request_json(
        self,
        *,
        endpoint: str,
        api_key: str,
        body: dict[str, Any],
        timeout_seconds: float,
    ) -> tuple[dict[str, Any], str]:
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
                raw = response.read().decode("utf-8", errors="ignore")
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"model request timed out: {exc}") from exc
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                detail = ""
            raise RuntimeError(f"model request http error: {exc.code} {detail[:400]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"model request network error: {exc}") from exc
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        return payload, raw
