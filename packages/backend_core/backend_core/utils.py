from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any
import urllib.parse
import uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def isoformat_utc(value: datetime | None) -> str:
    if value is None:
        return utcnow().isoformat()
    return ensure_utc(value).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def safe_filename(name: str, fallback: str = "file") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    cleaned = cleaned.strip("._-")
    return cleaned or fallback


def truncate_text(value: str | None, limit: int = 1000) -> str | None:
    if value is None:
        return None
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def looks_like_qwen_model(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return False
    return normalized.startswith(("qwen", "qwq"))


def parse_json_bytes(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="ignore").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {"value": parsed}


def llm_api_base(endpoint: str) -> str:
    normalized = str(endpoint or "").strip().rstrip("/")
    if not normalized:
        return ""
    for suffix in ("/chat/completions", "/responses"):
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def should_use_responses_api(
    *,
    provider: str | None,
    endpoint: str | None,
    model_name: str | None = None,
) -> bool:
    if looks_like_qwen_model(model_name):
        return True

    provider_name = str(provider or "").strip().lower()
    if provider_name in {"qwen", "aliyun-bailian"}:
        return True

    normalized = str(endpoint or "").strip().rstrip("/")
    if not normalized:
        return False
    if normalized.endswith("/responses"):
        return True
    if normalized.endswith("/chat/completions"):
        return False

    parsed = urllib.parse.urlparse(normalized)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower().rstrip("/")
    if host.endswith("dashscope.aliyuncs.com"):
        return True
    return path.endswith("/v1")


def resolve_llm_request_endpoint(
    endpoint: str,
    *,
    use_responses_api: bool,
) -> str:
    base = llm_api_base(endpoint)
    if not base:
        return ""
    suffix = "/responses" if use_responses_api else "/chat/completions"
    return f"{base}{suffix}"


def build_text_request_body(
    *,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    use_responses_api: bool,
    enable_thinking: bool = False,
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


def _collect_llm_text_chunks(value: Any) -> list[str]:
    if isinstance(value, str):
        normalized = value.strip()
        return [normalized] if normalized else []
    if isinstance(value, list):
        chunks: list[str] = []
        for item in value:
            chunks.extend(_collect_llm_text_chunks(item))
        return chunks
    if isinstance(value, dict):
        chunks: list[str] = []
        for key in ("text", "output_text"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                chunks.append(item.strip())
        for key in ("content", "parts"):
            item = value.get(key)
            if isinstance(item, (str, list, dict)):
                chunks.extend(_collect_llm_text_chunks(item))
        return chunks
    return []


def extract_llm_text_response(payload: dict[str, Any], raw_text: str) -> str:
    candidates: list[str] = []

    if isinstance(payload.get("choices"), list):
        for choice in payload["choices"]:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if isinstance(message, dict):
                candidates.extend(_collect_llm_text_chunks(message.get("content")))
            candidates.extend(_collect_llm_text_chunks(choice.get("text")))

    candidates.extend(_collect_llm_text_chunks(payload.get("output_text")))

    output = payload.get("output")
    if isinstance(output, (dict, list, str)):
        candidates.extend(_collect_llm_text_chunks(output))

    if isinstance(payload.get("message"), dict):
        candidates.extend(_collect_llm_text_chunks(payload["message"].get("content")))

    for candidate in candidates:
        normalized = candidate.strip()
        if normalized:
            return normalized
    return raw_text.strip()


def extract_json_object(text: str) -> str:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.IGNORECASE | re.DOTALL)
    if fenced is not None:
        stripped = fenced.group(1).strip()
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        return stripped[first : last + 1]
    return stripped


def _normalize_json_text(text: str) -> tuple[str, list[str]]:
    normalized = text.replace("\ufeff", "").replace("\u200b", "").strip()
    repairs: list[str] = []
    if normalized != text:
        repairs.append("trimmed_wrapper_characters")
    if normalized.lower().startswith("json"):
        remainder = normalized[4:].lstrip()
        if remainder.startswith("{") or remainder.startswith("["):
            normalized = remainder
            repairs.append("removed_json_prefix")
    return normalized, repairs


def _find_string_end(text: str, start: int) -> int:
    escape = False
    index = start + 1
    while index < len(text):
        char = text[index]
        if escape:
            escape = False
        elif char == "\\":
            escape = True
        elif char == '"':
            return index + 1
        index += 1
    return len(text)


def _skip_whitespace(text: str, start: int) -> int:
    index = start
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _looks_like_object_key(text: str, start: int) -> bool:
    if start >= len(text) or text[start] != '"':
        return False
    string_end = _find_string_end(text, start)
    next_index = _skip_whitespace(text, string_end)
    return next_index < len(text) and text[next_index] == ":"


def _starts_value_token(text: str, start: int) -> bool:
    if start >= len(text):
        return False
    char = text[start]
    if char in {'"', "{", "[", "-"}:
        return True
    if char.isdigit():
        return True
    return text.startswith("true", start) or text.startswith("false", start) or text.startswith("null", start)


def _mark_parent_value_complete(stack: list[dict[str, str]]) -> None:
    if not stack:
        return
    context = stack[-1]
    if context["kind"] == "object" and context["state"] == "value":
        context["state"] = "comma_or_end"
    elif context["kind"] == "array" and context["state"] == "value_or_end":
        context["state"] = "comma_or_end"


def _insert_missing_commas(text: str) -> str:
    result: list[str] = []
    stack: list[dict[str, str]] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace():
            result.append(char)
            index += 1
            continue

        if stack:
            context = stack[-1]
            if context["kind"] == "object" and context["state"] == "comma_or_end":
                if char == '"' and _looks_like_object_key(text, index):
                    result.append(",")
                    context["state"] = "key_or_end"
            elif context["kind"] == "array" and context["state"] == "comma_or_end":
                if char not in {",", "]"} and _starts_value_token(text, index):
                    result.append(",")
                    context["state"] = "value_or_end"

        char = text[index]
        if char == "{":
            result.append(char)
            stack.append({"kind": "object", "state": "key_or_end"})
            index += 1
            continue
        if char == "[":
            result.append(char)
            stack.append({"kind": "array", "state": "value_or_end"})
            index += 1
            continue
        if char == "}":
            result.append(char)
            if stack and stack[-1]["kind"] == "object":
                stack.pop()
            _mark_parent_value_complete(stack)
            index += 1
            continue
        if char == "]":
            result.append(char)
            if stack and stack[-1]["kind"] == "array":
                stack.pop()
            _mark_parent_value_complete(stack)
            index += 1
            continue
        if char == ",":
            result.append(char)
            if stack:
                context = stack[-1]
                if context["kind"] == "object":
                    context["state"] = "key_or_end"
                elif context["kind"] == "array":
                    context["state"] = "value_or_end"
            index += 1
            continue
        if char == ":":
            result.append(char)
            if stack and stack[-1]["kind"] == "object" and stack[-1]["state"] == "colon":
                stack[-1]["state"] = "value"
            index += 1
            continue
        if char == '"':
            string_end = _find_string_end(text, index)
            result.append(text[index:string_end])
            if stack:
                context = stack[-1]
                if context["kind"] == "object":
                    if context["state"] == "key_or_end" and _looks_like_object_key(text, index):
                        context["state"] = "colon"
                    elif context["state"] == "value":
                        context["state"] = "comma_or_end"
                elif context["kind"] == "array" and context["state"] == "value_or_end":
                    context["state"] = "comma_or_end"
            index = string_end
            continue

        number_match = re.match(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?", text[index:])
        if number_match is not None:
            token = number_match.group(0)
            result.append(token)
            if stack:
                context = stack[-1]
                if context["kind"] == "object" and context["state"] == "value":
                    context["state"] = "comma_or_end"
                elif context["kind"] == "array" and context["state"] == "value_or_end":
                    context["state"] = "comma_or_end"
            index += len(token)
            continue

        literal = next(
            (item for item in ("true", "false", "null") if text.startswith(item, index)),
            None,
        )
        if literal is not None:
            result.append(literal)
            if stack:
                context = stack[-1]
                if context["kind"] == "object" and context["state"] == "value":
                    context["state"] = "comma_or_end"
                elif context["kind"] == "array" and context["state"] == "value_or_end":
                    context["state"] = "comma_or_end"
            index += len(literal)
            continue

        result.append(char)
        index += 1

    return "".join(result)


def _repair_json_text(text: str) -> tuple[str, list[str]]:
    repaired = text
    repairs: list[str] = []

    without_trailing_commas = re.sub(r",(?=\s*[}\]])", "", repaired)
    if without_trailing_commas != repaired:
        repaired = without_trailing_commas
        repairs.append("removed_trailing_commas")

    with_missing_commas_restored = _insert_missing_commas(repaired)
    if with_missing_commas_restored != repaired:
        repaired = with_missing_commas_restored
        repairs.append("inserted_missing_commas")

    return repaired, repairs


def parse_json_object(text: str) -> tuple[dict[str, Any], list[str]]:
    extracted = extract_json_object(text)
    normalized, normalize_repairs = _normalize_json_text(extracted)
    repaired, repair_steps = _repair_json_text(normalized)

    candidates: list[tuple[str, list[str]]] = [(extracted, [])]
    if normalized != extracted:
        candidates.append((normalized, normalize_repairs))
    if repaired != normalized:
        candidates.append((repaired, normalize_repairs + repair_steps))

    last_error: json.JSONDecodeError | None = None
    for candidate, repairs in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if not isinstance(parsed, dict):
            raise ValueError("top-level JSON must be an object")
        return parsed, repairs

    if last_error is not None:
        raise last_error
    raise ValueError("unable to parse JSON object")


def describe_json_error_context(text: str, position: int, radius: int = 120) -> str:
    start = max(0, position - radius)
    end = min(len(text), position + radius)
    excerpt = text[start:end]
    marker = position - start
    return excerpt[:marker] + "<<<<HERE>>>>" + excerpt[marker:]


def json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
