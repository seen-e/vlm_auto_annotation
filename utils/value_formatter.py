"""Format exported values for prompt injection."""

from __future__ import annotations

import json
from typing import Any


def _json(value: Any, *, compact: bool) -> str:
    if compact:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(value, ensure_ascii=False, indent=2)


def _bullet(value: Any) -> str:
    items = value if isinstance(value, list) else ([] if value in (None, "") else [value])
    lines = []
    for item in items:
        if isinstance(item, (dict, list)):
            text = _json(item, compact=True)
        else:
            text = str(item)
        lines.append(f"- {text}")
    return "\n".join(lines)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_text(val)}" for key, val in value.items())
    if isinstance(value, list):
        return "; ".join(_text(item) for item in value)
    return str(value)


def format_value(value: Any, fmt: str = "json") -> Any:
    """Return a prompt-ready representation while preserving raw exports elsewhere."""
    fmt = str(fmt or "json").strip().lower()
    if fmt == "raw":
        return value
    if fmt == "json":
        return _json(value, compact=False)
    if fmt == "compact_json":
        return _json(value, compact=True)
    if fmt == "bullet":
        return _bullet(value)
    if fmt == "text":
        return _text(value)
    return _json(value, compact=False)
