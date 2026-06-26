"""Centralized logging configuration for the JianDou backend."""
from __future__ import annotations

import logging
import sys

_DEFAULT_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
_JSON_FORMAT = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'


def configure_logging(
    *,
    level: int = logging.INFO,
    json_format: bool = False,
) -> None:
    """Configure root and application loggers.

    Parameters
    ----------
    level : int
        Log level for the application.
    json_format : bool
        When ``True`` emit structured JSON log lines (useful in production).
    """
    fmt = _JSON_FORMAT if json_format else _DEFAULT_FORMAT
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S"))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers at INFO level
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Application loggers
    logging.getLogger("jiandou").setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the ``jiandou.`` prefix."""
    return logging.getLogger(f"jiandou.{name}")
