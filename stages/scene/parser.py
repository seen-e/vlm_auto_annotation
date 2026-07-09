"""Scene parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from ...contracts.scene import SceneStageOutput


@dataclass
class ParseResult:
    output: Any
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_scene(raw_json: dict[str, Any] | None, context: Any, media_meta: dict[str, Any]) -> ParseResult:
    data = raw_json or {}
    try:
        output = SceneStageOutput(**data)
        warnings = []
        if not output.primary_view:
            views = media_meta.get("selected_views") or []
            output.primary_view = str(views[0]) if views else None
        if not output.executors:
            warnings.append(f"video_id={context.video_id or 'unknown'} stage=scene: no executors")
        return ParseResult(output=output, warnings=warnings)
    except (ValidationError, TypeError, ValueError) as exc:
        return ParseResult(output=SceneStageOutput(), errors=[str(exc)[:160]])
