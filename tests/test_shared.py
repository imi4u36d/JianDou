"""Tests for backend/shared.py — unified utility functions."""
from __future__ import annotations

import pytest
pytestmark = pytest.mark.unit
import pytest

from backend.shared import (
    find_nested_string,
    first_non_blank,
    first_positive_int,
    map_value,
    nested_boolean,
    nested_int,
    nested_nullable_int,
    nested_string_list,
    nested_value,
    now_iso,
    positive_int,
    random_id,
    read_json,
    safe_bool,
    safe_float,
    safe_int,
    string_value,
    trim,
    truncate_text,
    write_json,
)


class TestStringValue:
    def test_normal_string(self):
        assert string_value(" hello ") == "hello"

    def test_none(self):
        assert string_value(None) == ""

    def test_int(self):
        assert string_value(42) == "42"


class TestFirstNonBlank:
    def test_first(self):
        assert first_non_blank("a", "b") == "a"

    def test_skips_blank(self):
        assert first_non_blank("", "  ", "c") == "c"

    def test_all_blank(self):
        assert first_non_blank("", None) == ""


class TestTrim:
    def test_trimmed(self):
        assert trim("  x  ") == "x"

    def test_fallback(self):
        assert trim(None, "default") == "default"

    def test_empty_to_fallback(self):
        assert trim("  ") == ""


class TestSafeInt:
    def test_int_unchanged(self):
        assert safe_int(5) == 5

    def test_float_truncated(self):
        assert safe_int(3.9) == 3

    def test_string_parsed(self):
        assert safe_int("42") == 42

    def test_invalid_fallback(self):
        assert safe_int("abc", 99) == 99

    def test_none_fallback(self):
        assert safe_int(None) == 0


class TestSafeFloat:
    def test_float_unchanged(self):
        assert safe_float(3.14) == 3.14

    def test_int_promoted(self):
        assert safe_float(3) == 3.0

    def test_none_fallback(self):
        assert safe_float(None) == 0.0


class TestSafeBool:
    @pytest.mark.parametrize("input,expected", [
        (True, True), (False, False), (1, True), (0, False),
        ("true", True), ("false", False), ("1", True), ("yes", True),
    ])
    def test_values(self, input, expected):
        assert safe_bool(input) is expected


class TestPositiveInt:
    def test_positive(self):
        assert positive_int(5, 10) == 5

    def test_zero_fallback(self):
        assert positive_int(0, 10) == 10


class TestFirstPositiveInt:
    def test_first(self):
        assert first_positive_int(0, 3, 5) == 3

    def test_none_positive(self):
        assert first_positive_int(0, -1, 0) == 0


class TestMapValue:
    def test_dict_unchanged(self):
        d = {"a": 1}
        assert map_value(d) is d

    def test_non_dict(self):
        assert map_value("nope") == {}


class TestReadJson:
    def test_valid(self):
        assert read_json('{"a": 1}') == {"a": 1}

    def test_invalid(self):
        assert read_json("{bad}") == {}

    def test_none(self):
        assert read_json(None) == {}


class TestWriteJson:
    def test_roundtrip(self):
        assert write_json({"a": 1}) == '{"a":1}'


class TestNestedAccessors:
    def test_nested_value(self):
        assert nested_value({"x": {"y": "z"}}, "x", "y") == "z"
        assert nested_value({}, "x", "y") == ""

    def test_nested_int(self):
        assert nested_int({"x": {"y": "42"}}, "x", "y") == 42

    def test_nested_nullable_int(self):
        assert nested_nullable_int({"x": {"y": None}}, "x", "y") is None

    def test_nested_boolean(self):
        assert nested_boolean({"x": {"y": "true"}}, "x", "y") is True

    def test_nested_string_list(self):
        assert nested_string_list({"x": {"y": ["a", "b"]}}, "x", "y") == ["a", "b"]

    def test_find_nested_string(self):
        assert find_nested_string({"a": {"b": {"c": "val"}}}, "a", "b", "c") == "val"
        assert find_nested_string({}, "a") == ""


class TestNowIso:
    def test_returns_string(self):
        assert isinstance(now_iso(), str)
        assert "T" in now_iso()


class TestRandomId:
    def test_returns_32_hex_chars(self):
        rid = random_id()
        assert len(rid) == 32
        assert all(c in "0123456789abcdef" for c in rid)

    def test_unique(self):
        assert random_id() != random_id()


class TestTruncateText:
    def test_within_limit(self):
        assert truncate_text("hello", 10) == "hello"

    def test_over_limit(self):
        assert truncate_text("hello world", 5) == "hello"

    def test_none(self):
        assert truncate_text(None, 10) == ""
