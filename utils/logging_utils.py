"""Logging helpers for CLI entrypoints."""

from __future__ import annotations

import logging

from .config import DEFAULT_LOG_FORMAT, DEFAULT_LOG_LEVEL


def configure_logging(level: str = DEFAULT_LOG_LEVEL, log_format: str = DEFAULT_LOG_FORMAT) -> None:
    """Configure root logging once for command-line entrypoints."""
    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format=log_format, force=True)
