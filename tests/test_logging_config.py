"""Tests for backend/logging_config.py."""
from __future__ import annotations

import logging

import pytest

from backend.logging_config import configure_logging, get_logger

pytestmark = pytest.mark.unit


class TestConfigureLogging:
    def test_does_not_raise(self):
        configure_logging()

    def test_json_format_does_not_raise(self):
        configure_logging(json_format=True)

    def test_root_logger_has_handler(self):
        configure_logging()
        root = logging.getLogger()
        assert len(root.handlers) >= 1


class TestGetLogger:
    def test_returns_logger_with_jiandou_prefix(self):
        logger = get_logger("test")
        assert logger.name == "jiandou.test"

    def test_returns_same_logger_for_same_name(self):
        a = get_logger("a")
        b = get_logger("a")
        assert a is b


class TestNoisyLoggersQuiet:
    def test_third_party_loggers_are_warning_level(self):
        configure_logging(level=logging.INFO)
        for name in ("httpx", "httpcore", "urllib3"):
            lg = logging.getLogger(name)
            assert lg.level <= logging.WARNING
