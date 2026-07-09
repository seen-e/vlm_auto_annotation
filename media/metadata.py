"""Media metadata helpers."""

from __future__ import annotations

from typing import Any


def primary_view_from_meta(meta: dict[str, Any]) -> str:
    views = meta.get("selected_views") or meta.get("merge_view_names") or []
    return str(views[0]) if views else "unknown"
