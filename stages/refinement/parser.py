"""Refinement parser."""

from __future__ import annotations

from typing import Any

from ...annotation_pipeline.parsers import parse_refinement_output


def parse_refinement(raw_json: dict[str, Any] | None, context: Any, media_meta: dict[str, Any]):
    scene = context.stage_contracts["scene"]
    analysis = context.stage_contracts["analysis"]
    return parse_refinement_output(raw_json, analysis=analysis, scene=scene, video_id=context.video_id)
