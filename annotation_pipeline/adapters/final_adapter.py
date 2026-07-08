"""Build compact final annotation output."""

from __future__ import annotations

from typing import Any

from ..schemas import FinalAnnotationOutput, RefinementStageOutput, SceneStageOutput


def build_final_annotation(
    *,
    scene: SceneStageOutput,
    refinement: RefinementStageOutput,
    video_id: str | None = None,
    model: str | None = None,
    flow_name: str = "vla_phase_annotation",
) -> FinalAnnotationOutput:
    """Convert refined segments to the compact final annotation format."""
    action_sequence: list[dict[str, Any]] = []
    touched_objects: list[str] = []
    caption_parts: list[str] = []

    for segment in refinement.refined_segments:
        item = {
            "segment_id": segment.segment_id,
            "start_time": segment.start_time,
            "end_time": segment.end_time,
            "executor": segment.executor,
            "action": segment.action,
            "objects": segment.objects,
            "confidence": segment.confidence,
        }
        if segment.start_frame is not None:
            item["start_frame"] = segment.start_frame
        if segment.end_frame is not None:
            item["end_frame"] = segment.end_frame
        if segment.boundary_reason:
            item["boundary_reason"] = segment.boundary_reason
        action_sequence.append(item)
        touched_objects.extend(segment.objects)
        obj_text = ", ".join(segment.objects) if segment.objects else "no_object"
        time_text = f"{segment.start_time or '?'}-{segment.end_time or '?'}"
        caption_parts.append(f"{time_text} {segment.executor} {segment.action} {obj_text}".strip())

    return FinalAnnotationOutput(
        video_id=video_id,
        task_summary=scene.scene_summary or ("; ".join(caption_parts[:2]) if caption_parts else ""),
        action_sequence=action_sequence,
        touched_objects=touched_objects,
        final_caption="; ".join(caption_parts),
        metadata={
            "schema_version": "stage_contracts_v1",
            "flow_name": flow_name,
            "model": model or "",
        },
    )
