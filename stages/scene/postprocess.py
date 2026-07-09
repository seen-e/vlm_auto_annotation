"""Scene postprocessing."""

from __future__ import annotations

from typing import Any


def postprocess_scene(contract: Any, context: Any, media_meta: dict[str, Any]):
    if not getattr(contract, "primary_view", None):
        views = media_meta.get("selected_views") or []
        contract.primary_view = str(views[0]) if views else None
    return contract
