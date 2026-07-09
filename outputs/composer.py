"""Final AnnotationResult composer for the current workflow architecture."""

from __future__ import annotations

from typing import Any

from ..contracts.final import FinalAnnotationOutput
from ..utils.results import AnnotationResult, StageResult


def _stage_result(result: Any) -> StageResult:
    return StageResult(
        name=result.name,
        output=result.parsed_output,
        raw_response=result.raw_response,
        success=result.success,
        error="; ".join(result.errors) if result.errors else None,
        token_usage=result.usage,
    )


def _final_annotation(context: Any) -> FinalAnnotationOutput:
    scene = context.stage_contracts.get("scene")
    refinement = context.stage_contracts.get("refinement")
    action_sequence: list[dict[str, Any]] = []
    touched_objects: list[str] = []
    caption_parts: list[str] = []
    if refinement is not None:
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
            caption_parts.append(f"{segment.start_time or '?'}-{segment.end_time or '?'} {segment.executor} {segment.action} {obj_text}")
    task_summary = getattr(scene, "scene_summary", "") or "; ".join(caption_parts[:2])
    return FinalAnnotationOutput(
        video_id=context.video_id,
        task_summary=task_summary,
        action_sequence=action_sequence,
        touched_objects=touched_objects,
        final_caption="; ".join(caption_parts),
        metadata={
            "schema_version": "current",
            "workflow_name": context.workflow_name,
            "model": context.model,
        },
    )


def _scene_output(context: Any) -> dict[str, Any]:
    scene = context.stage_contracts.get("scene")
    if scene is None:
        return {}
    return {
        "primary_view": scene.primary_view or "",
        "executors": [item.model_dump(mode="json") for item in scene.executors],
        "touched_objects": [item.model_dump(mode="json") for item in scene.touched_objects],
        "background_objects": [item.model_dump(mode="json") for item in scene.background_objects],
        "scene_summary": scene.scene_summary,
    }


def compose_annotation_result(context: Any, run_results: dict[str, Any], config: dict[str, Any]) -> AnnotationResult:
    output_cfg = {}
    output_cfg.update((config.get("workflow") or {}).get("output") or {})
    output_cfg.update(config.get("output") or {})

    total_seconds = sum(float(result.elapsed_seconds or 0.0) for result in run_results.values())
    final = _final_annotation(context)
    output: dict[str, Any] = {
        "schema_version": "current",
        "video_id": context.video_id,
        "workflow_name": context.workflow_name,
        "experiment_name": context.experiment_name,
        "task": {
            "instruction": context.instruction,
            "summary": final.task_summary,
        },
        "scene": _scene_output(context),
        "segments": final.action_sequence,
        "exports": context.exports,
        "metadata": {
            "model": context.model,
            "prompt_language": context.prompt_language,
            "robot_type": context.robot_type,
            "elapsed_seconds": total_seconds,
        },
        "validation": {"warnings": list(context.validation_warnings), "errors": []},
    }

    if output_cfg.get("include_contracts", False):
        output["contracts"] = {
            name: contract.model_dump(mode="json") if hasattr(contract, "model_dump") else contract
            for name, contract in context.stage_contracts.items()
        }
    if output_cfg.get("include_debug", False):
        output["debug"] = {
            "stage_metadata": {
                name: {
                    "elapsed_seconds": result.elapsed_seconds,
                    "usage": result.usage,
                    "media_meta": result.media_meta,
                    "warnings": result.warnings,
                    "errors": result.errors,
                }
                for name, result in run_results.items()
            },
            "export_status": context.export_status,
        }
    if output_cfg.get("include_trace", False):
        output["trace"] = {
            "stage_outputs": context.stage_outputs,
            "stage_contracts": {
                name: contract.model_dump(mode="json") if hasattr(contract, "model_dump") else contract
                for name, contract in context.stage_contracts.items()
            },
            "formatted_exports": context.formatted_exports,
            "raw_responses": {name: result.raw_response for name, result in run_results.items()},
        }

    include_stage_objects = bool(output_cfg.get("include_stage_objects", False)) or bool(output_cfg.get("include_trace", False))
    stages = {name: _stage_result(result) for name, result in run_results.items()} if include_stage_objects else {}
    return AnnotationResult(workflow_name=context.workflow_name, stages=stages, output=output)
