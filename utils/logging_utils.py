"""Logging helpers for CLI entrypoints."""

from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(level: str = "INFO", log_format: str = LOG_FORMAT) -> None:
    """Configure root logging once for command-line entrypoints."""
    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format=log_format, force=True)
