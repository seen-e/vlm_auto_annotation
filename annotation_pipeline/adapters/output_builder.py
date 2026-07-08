"""Output builders for lightweight / debug / trace / legacy output layers.

Each builder returns a plain dict that can be merged into the final output.
The builders are intentionally independent: callers compose them as needed.
"""

from __future__ import annotations

from typing import Any

from ..schemas import (
    AnalysisStageOutput,
    RefinementStageOutput,
    SceneStageOutput,
)


def build_lightweight_output(
    *,
    final_annotation: Any,
    scene_contract: SceneStageOutput,
    video_id: str | None,
    initial_instruction: str,
    refined_instruction: str,
    prompt_language: str,
    robot_type: str,
    model: str,
    flow_name: str,
    schema_version: str,
    elapsed_seconds: float,
) -> dict[str, Any]:
    """Build the default lightweight output suitable for downstream training/eval.

    This is the stable public contract.  It intentionally excludes:
      - candidate_segments / refined_segments / changes (intermediate results)
      - full stage contracts, raw VLM output
      - prompts, media parts, base64
      - legacy compatibility fields
    """

    scene_summary: dict[str, Any] = {
        "primary_view": scene_contract.primary_view or "",
        "executors": [
            {
                "executor_id": item.executor_id,
                "description": item.description,
                "main_workspace": item.main_workspace,
            }
            for item in scene_contract.executors
        ],
        "touched_objects": [
            {
                "object_id": item.object_id,
                "description": item.description,
                "role": item.role,
            }
            for item in scene_contract.touched_objects
        ],
        "background_objects": [
            {
                "object_id": item.object_id,
                "description": item.description,
                "role": item.role,
            }
            for item in scene_contract.background_objects
        ],
    }

    return {
        "schema_version": schema_version,
        "video_id": video_id,
        "flow_name": flow_name,
        "task": {
            "initial_instruction": initial_instruction,
            "refined_instruction": refined_instruction,
            "summary": final_annotation.task_summary,
        },
        "scene": scene_summary,
        "segments": final_annotation.action_sequence,
        "metadata": {
            "model": model or "",
            "prompt_language": prompt_language,
            "robot_type": robot_type,
            "elapsed_seconds": elapsed_seconds,
        },
    }


def build_debug_output(
    *,
    validation_warnings: list[str],
    timing: dict[str, float],
    stage_metadata: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build lightweight debug information.

    Contains validation warnings, timing breakdown, and stage metadata.
    Does NOT contain raw VLM output, prompts, or media parts.
    """

    return {
        "debug": {
            "validation": {
                "warnings": list(validation_warnings),
            },
            "timing": timing,
            "stage_metadata": stage_metadata,
        },
    }


def build_trace_output(
    *,
    scene_stage: Any,
    analysis_stage: Any,
    refinement_stage: Any,
    scene_contract: SceneStageOutput,
    analysis_contract: AnalysisStageOutput,
    refinement_contract: RefinementStageOutput,
) -> dict[str, Any]:
    """Build trace output for full-process reproduction.

    Contains stage raw outputs and parsed contracts.
    Does NOT contain media parts / base64 data.
    """

    def _safe_stage_output(stage: Any) -> dict[str, Any]:
        """Extract the serializable output dict from a StageResult, if available."""
        if hasattr(stage, "output") and isinstance(stage.output, dict):
            return stage.output
        if isinstance(stage, dict):
            return stage
        return {}

    return {
        "trace": {
            "stage_outputs": {
                "scene": _safe_stage_output(scene_stage),
                "analysis": _safe_stage_output(analysis_stage),
                "refinement": _safe_stage_output(refinement_stage),
            },
            "stage_contracts": {
                "scene": scene_contract.model_dump(mode="json"),
                "analysis": analysis_contract.model_dump(mode="json"),
                "refinement": refinement_contract.model_dump(mode="json"),
            },
        },
    }


def build_legacy_output(
    *,
    robot_type: str,
    scene_context: dict[str, Any],
    action_sequence: list[dict[str, Any]],
    main_object: str,
    timestamped_actions: list[dict[str, Any]],
    steps: list[str],
    refined_instruction: str,
) -> dict[str, Any]:
    """Build deprecated legacy compatibility output.

    Only included when ``include_legacy_fields=True``.

    .. deprecated::
        New downstream code should use ``segments`` / ``scene`` / ``task``
        from the lightweight output instead.
    """

    return {
        "legacy_output": {
            "analysisResult": {
                "robot_type": robot_type,
                "sceneContext": scene_context,
                "action_sequence": action_sequence,
                "main_object": main_object,
            },
            "sceneContext": scene_context,
            "timestampedActionSequence": timestamped_actions,
            "fineGrainedSteps": steps,
            "refinedInstruction": refined_instruction,
        },
    }
