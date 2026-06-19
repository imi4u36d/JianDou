from __future__ import annotations

from backend.domain.json_payloads import (
    list_value,
    object_value,
    read_json_list,
    read_json_object,
    read_json_value,
    write_json_object,
    write_json_value,
)


def test_read_json_object_accepts_only_object_payloads() -> None:
    assert read_json_object('{"a": 1}') == {"a": 1}
    assert read_json_object("[1, 2]") == {}
    assert read_json_object("{bad") == {}
    assert read_json_object(None) == {}


def test_read_json_list_accepts_only_list_payloads() -> None:
    assert read_json_list("[1, 2]") == [1, 2]
    assert read_json_list('{"a": 1}') == []
    assert read_json_list("{bad") == []


def test_read_json_value_uses_fallback_for_invalid_or_null_payloads() -> None:
    fallback = {"safe": True}

    assert read_json_value("{bad", fallback) is fallback
    assert read_json_value("null", fallback) is fallback
    assert read_json_value('"text"', fallback) == "text"


def test_object_and_list_value_filter_runtime_values() -> None:
    assert object_value({"a": 1}) == {"a": 1}
    assert object_value(["bad"]) == {}
    assert list_value([1, 2]) == [1, 2]
    assert list_value({"bad": True}) == []


def test_write_json_helpers_preserve_non_ascii_and_filter_objects() -> None:
    assert write_json_value({"title": "分镜"}) == '{"title": "分镜"}'
    assert write_json_object(["bad"]) == "{}"
