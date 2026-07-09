"""Lightweight output."""

from __future__ import annotations

from typing import Any

from ..annotation_pipeline.adapters.final_adapter import build_final_annotation


def build_lightweight(context: Any) -> dict[str, Any]:
    scene = context.stage_contracts.get("scene")
    refinement = context.stage_contracts.get("refinement")
    if scene is None or refinement is None:
        return {}
    final = build_final_annotation(
        scene=scene,
        refinement=refinement,
        video_id=context.video_id,
        model=context.model,
        flow_name=context.workflow_name or "vla_phase_annotation",
    )
    return final.model_dump()
