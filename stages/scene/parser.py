"""Scene parser."""

from __future__ import annotations

from typing import Any

from ...annotation_pipeline.parsers import parse_scene_output


def parse_scene(raw_json: dict[str, Any] | None, context: Any, media_meta: dict[str, Any]):
    return parse_scene_output(raw_json, meta=media_meta, video_id=context.video_id)
