"""Logging helpers for CLI entrypoints."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path

from .config import DEFAULT_LOG_DIR, DEFAULT_LOG_FORMAT, DEFAULT_LOG_LEVEL, DEFAULT_LOG_TO_FILE


def _resolve_log_dir(log_dir: str) -> Path:
    path = Path(log_dir)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    return path


def configure_logging(
    level: str | None = DEFAULT_LOG_LEVEL,
    log_format: str | None = DEFAULT_LOG_FORMAT,
    *,
    log_to_file: bool | None = DEFAULT_LOG_TO_FILE,
    log_dir: str | None = DEFAULT_LOG_DIR,
    log_name: str = "vlm_auto_annotation",
) -> Path | None:
    """Configure root logging once for command-line entrypoints."""
    level = level or DEFAULT_LOG_LEVEL
    log_format = log_format or DEFAULT_LOG_FORMAT
    log_to_file = DEFAULT_LOG_TO_FILE if log_to_file is None else log_to_file
    log_dir = log_dir or DEFAULT_LOG_DIR
    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    formatter = logging.Formatter(log_format)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers: list[logging.Handler] = [console_handler]

    log_path: Path | None = None
    if log_to_file:
        resolved_log_dir = _resolve_log_dir(log_dir)
        resolved_log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = resolved_log_dir / f"{log_name}_{timestamp}.log"
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(level=numeric_level, handlers=handlers, force=True)
    logging.getLogger(__name__).debug("Logging configured level=%s log_file=%s", level, log_path)
    return log_path
