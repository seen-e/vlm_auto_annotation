"""Safe dotted-path extraction for stage export rules."""

from __future__ import annotations

import re
from typing import Any


_TOKEN_RE = re.compile(r"([^\.\[\]]+)|\[(\*|\d+)\]")


_MISSING = object()


def _tokens(path: str) -> list[str | int]:
    tokens: list[str | int] = []
    for part in str(path or "").split("."):
        if not part:
            continue
        for match in _TOKEN_RE.finditer(part):
            key, index = match.groups()
            if key is not None:
                tokens.append(key)
            elif index == "*":
                tokens.append("*")
            else:
                tokens.append(int(index))
    return tokens


def _get_one(value: Any, token: str | int) -> Any:
    if isinstance(token, int):
        if isinstance(value, (list, tuple)) and 0 <= token < len(value):
            return value[token]
        return _MISSING
    if isinstance(value, dict) and token in value:
        return value[token]
    if not isinstance(value, dict) and hasattr(value, token):
        return getattr(value, token)
    return _MISSING


def _flatten_once(items: list[Any]) -> list[Any]:
    out: list[Any] = []
    for item in items:
        if isinstance(item, list):
            out.extend(item)
        else:
            out.append(item)
    return out


def extract_path(data: Any, path: str, default: Any = None) -> tuple[Any, bool]:
    """Extract ``path`` from dict/list/model data without raising.

    Supports ``a.b``, ``items[0].name`` and ``items[*].name``. Returns
    ``(value, success)``.
    """
    tokens = _tokens(path)
    if not tokens:
        return data, True

    current = data
    for token in tokens:
        if token == "*":
            if not isinstance(current, (list, tuple)):
                return default, False
            current = list(current)
            continue
        if isinstance(current, list):
            values = []
            for item in current:
                next_value = _get_one(item, token)
                if next_value is not _MISSING:
                    values.append(next_value)
            if not values:
                return default, False
            current = _flatten_once(values)
        else:
            next_value = _get_one(current, token)
            if next_value is _MISSING:
                return default, False
            current = next_value
    return current, True
