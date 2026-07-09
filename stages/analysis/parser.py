"""Analysis parser."""

from __future__ import annotations

from typing import Any

from ...annotation_pipeline.parsers import parse_analysis_output


def parse_analysis(raw_json: dict[str, Any] | None, context: Any, media_meta: dict[str, Any]):
    scene = context.stage_contracts["scene"]
    return parse_analysis_output(raw_json, scene=scene, video_id=context.video_id)
