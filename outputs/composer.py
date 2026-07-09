"""Final AnnotationResult composer."""

from __future__ import annotations

from typing import Any

from ..utils.results import AnnotationResult, StageResult
from ..annotation_pipeline.adapters import (
    build_debug_output,
    build_final_annotation,
    build_legacy_output,
    build_lightweight_output,
    build_trace_output,
)


def _stage_result(result: Any) -> StageResult:
    return StageResult(
        name=result.name,
        output=result.parsed_output,
        raw_response=result.raw_response,
        success=result.success,
        error="; ".join(result.errors) if result.errors else None,
        token_usage=result.usage,
    )


def compose_annotation_result(context: Any, run_results: dict[str, Any], config: dict[str, Any]) -> AnnotationResult:
    output_cfg = {}
    output_cfg.update((config.get("workflow") or {}).get("output") or {})
    output_cfg.update(config.get("output") or {})

    output: dict[str, Any] = {}
    scene_contract = context.stage_contracts.get("scene")
    analysis_contract = context.stage_contracts.get("analysis")
    refinement_contract = context.stage_contracts.get("refinement")
    total_seconds = sum(float(result.elapsed_seconds or 0.0) for result in run_results.values())
    refinement_raw = context.stage_outputs.get("refinement", {})
    refined_instruction = (
        refinement_raw.get("refinedInstruction")
        or refinement_raw.get("refined_instruction")
        or context.instruction
    )

    if output_cfg.get("include_lightweight", True) and scene_contract is not None and refinement_contract is not None:
        final_annotation = build_final_annotation(
            scene=scene_contract,
            refinement=refinement_contract,
            video_id=context.video_id,
            model=context.model,
            flow_name=context.workflow_name or "vla_phase_annotation",
        )
        output.update(
            build_lightweight_output(
                final_annotation=final_annotation,
                scene_contract=scene_contract,
                video_id=context.video_id,
                initial_instruction=context.instruction,
                refined_instruction=refined_instruction,
                prompt_language=context.prompt_language,
                robot_type=context.robot_type,
                model=context.model,
                flow_name=context.workflow_name or "vla_phase_annotation",
                schema_version=str(output_cfg.get("schema_version") or "v2"),
                elapsed_seconds=total_seconds,
            )
        )

    if output_cfg.get("include_validation", True):
        output["validation"] = {"warnings": list(context.validation_warnings), "errors": []}

    if output_cfg.get("include_intermediate_contracts", False):
        output["intermediate_contracts"] = {
            name: contract.model_dump(mode="json") if hasattr(contract, "model_dump") else contract
            for name, contract in context.stage_contracts.items()
        }

    if output_cfg.get("include_debug", False):
        timing: dict[str, float] = {}
        for name in ("scene", "analysis", "refinement"):
            result = run_results.get(name)
            timing[f"{name}_load_seconds"] = 0.0
            timing[f"{name}_postprocess_seconds"] = float(result.elapsed_seconds if result else 0.0)
        timing["total_seconds"] = total_seconds
        stage_metadata = {
            name: {"media_meta": result.media_meta, "usage": result.usage}
            for name, result in run_results.items()
        }
        output.update(
            build_debug_output(
                validation_warnings=list(context.validation_warnings),
                timing=timing,
                stage_metadata=stage_metadata,
            )
        )

    stage_objects = {name: _stage_result(result) for name, result in run_results.items()}
    if (
        output_cfg.get("include_trace", False)
        and scene_contract is not None
        and analysis_contract is not None
        and refinement_contract is not None
    ):
        output.update(
            build_trace_output(
                scene_stage=stage_objects.get("scene"),
                analysis_stage=stage_objects.get("analysis"),
                refinement_stage=stage_objects.get("refinement"),
                scene_contract=scene_contract,
                analysis_contract=analysis_contract,
                refinement_contract=refinement_contract,
            )
        )

    if output_cfg.get("include_legacy", False) and scene_contract is not None:
        analysis_raw = context.stage_outputs.get("analysis", {})
        scene_context = scene_contract.model_dump(mode="json") if hasattr(scene_contract, "model_dump") else {}
        action_sequence = analysis_raw.get("action_sequence") or analysis_raw.get("action_steps") or analysis_raw.get("candidate_segments") or []
        main_object = ""
        if getattr(scene_contract, "touched_objects", None):
            first = scene_contract.touched_objects[0]
            main_object = first.description or first.object_id
        timestamped_actions = (
            refinement_raw.get("action_sequence")
            or refinement_raw.get("timestampedActionSequence")
            or refinement_raw.get("timestamped_action_sequence")
            or []
        )
        if not timestamped_actions and refinement_contract is not None:
            timestamped_actions = [
                {
                    "executor": item.executor,
                    "action": item.action,
                    "object": item.objects[0] if item.objects else None,
                    "start_time": item.start_time,
                    "end_time": item.end_time,
                }
                for item in refinement_contract.refined_segments
            ]
        output.update(
            build_legacy_output(
                robot_type=context.robot_type,
                scene_context=scene_context,
                action_sequence=action_sequence,
                main_object=main_object,
                timestamped_actions=timestamped_actions,
                steps=refinement_raw.get("fineGrainedSteps") or refinement_raw.get("fine_grained_steps") or [],
                refined_instruction=refined_instruction,
            )
        )

    include_stage_objects = bool(output_cfg.get("include_stage_objects", False)) or bool(output_cfg.get("include_trace", False))
    stages = stage_objects if include_stage_objects else {}
    return AnnotationResult(flow_name=context.workflow_name or "vla_phase_annotation", stages=stages, output=output)
