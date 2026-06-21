from __future__ import annotations

import pytest
pytestmark = pytest.mark.service
from backend.services.generation_request_values import (
    find_nested_string,
    first_non_blank,
    map_value,
    nested_boolean,
    nested_int,
    nested_nullable_int,
    nested_string_list,
    nested_value,
    string_list,
    string_value,
)


def test_nested_value_helpers_keep_defaults_for_missing_or_invalid_shapes() -> None:
    payload = {"input": {"prompt": " hello ", "width": "1024.2", "seed": "42", "refs": [" a ", "", 1]}}

    assert nested_value(payload, "input", "prompt") == " hello "
    assert nested_value(payload, "missing", "prompt", "fallback") == "fallback"
    assert nested_int(payload, "input", "width", 512) == 1024
    assert nested_int(payload, "input", "bad", 512) == 512
    assert nested_nullable_int(payload, "input", "seed") == 42
    assert nested_nullable_int(payload, "input", "bad") is None
    assert nested_string_list(payload, "input", "refs") == ["a"]


def test_nested_boolean_accepts_common_wire_values() -> None:
    payload = {"input": {"yes": "yes", "no": "0", "number": 2, "unknown": "maybe"}}

    assert nested_boolean(payload, "input", "yes") is True
    assert nested_boolean(payload, "input", "no", True) is False
    assert nested_boolean(payload, "input", "number") is True
    assert nested_boolean(payload, "input", "unknown", True) is True
    assert nested_boolean(payload, "missing", "flag", True) is True


def test_collection_and_string_helpers_normalize_wire_values() -> None:
    assert map_value({1: "one", "two": 2}) == {"1": "one", "two": 2}
    assert map_value(["bad"]) == {}
    assert string_value(None) == ""
    assert string_value("  ok  ") == "ok"
    assert first_non_blank("", "  ", " value ") == "value"
    assert string_list([" a ", None, 3, ""]) == ["a", "3"]


def test_find_nested_string_recurses_through_provider_payloads() -> None:
    payload = {
        "output": [
            {"metadata": {"ignored": ""}},
            {"error": {"detail": "provider failed"}},
        ]
    }

    assert find_nested_string(payload, "message", "detail") == "provider failed"
