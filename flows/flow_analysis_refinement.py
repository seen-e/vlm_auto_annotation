"""Compatibility entrypoint for the configured VLA workflow.

The concrete stage logic now lives in ``stages/*`` and is orchestrated by
``core.workflow.WorkflowRunner``. This module only translates legacy keyword
arguments into the new workflow config.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..app.run_workflow import run_workflow
from ..utils.config import (
    DEFAULT_ANALYSIS_MERGE_VIEW_NAMES,
    DEFAULT_PROMPT_LANGUAGE,
    DEFAULT_REFINEMENT_MERGE_VIEW_NAMES,
    DEFAULT_ROBOT_TYPE,
    DEFAULT_SCENE_MERGE_VIEW_NAMES,
)
from ..utils.results import AnnotationResult
from ..utils.video_utils import load_video_or_views_as_media_parts


_STAGE_FIELDS = {
    "input_mode",
    "fps",
    "max_tokens",
    "max_frames",
    "resize_width",
    "merge_view_names",
    "jpeg_quality",
    "min_api_frames",
    "draw_timestamps",
    "draw_viewposition",
    "merge_views",
    "merge_mode",
    "merge_length",
}


def _scene_result_for_analysis(scene_output: dict[str, Any]) -> dict[str, Any]:
    """Return the compact scene subset consumed by analysis prompts."""
    allowed = {
        "primary_view",
        "spatial_reference_rule",
        "operation_units",
        "manipulated_objects",
        "video_summary",
    }
    return {key: scene_output[key] for key in allowed if key in scene_output}


def _stage_overrides(prefix: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field in _STAGE_FIELDS:
        key = f"{prefix}_{field}"
        if key in kwargs and kwargs[key] is not None:
            data[field] = kwargs[key]
    return data


def _legacy_overrides(
    *,
    model: str | None,
    include_debug: bool | None,
    include_trace: bool | None,
    include_legacy_fields: bool | None,
    include_stage_objects: bool | None,
    include_intermediate_contracts: bool | None,
    include_validation: bool | None,
    save_processed_stages: list[str] | tuple[str, ...] | None,
    save_processed_dir: str | Path | None,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    stages = {
        "scene": _stage_overrides("scene", kwargs),
        "analysis": _stage_overrides("analysis", kwargs),
        "refinement": _stage_overrides("refinement", kwargs),
    }
    for cfg in stages.values():
        cfg["_media_loader"] = load_video_or_views_as_media_parts
    if kwargs.get("max_frames") is not None:
        for cfg in stages.values():
            cfg["max_frames"] = kwargs["max_frames"]
    if kwargs.get("merge_views") is not None:
        for cfg in stages.values():
            cfg["merge_views"] = kwargs["merge_views"]
    stages["scene"].setdefault("merge_view_names", DEFAULT_SCENE_MERGE_VIEW_NAMES)
    stages["analysis"].setdefault("merge_view_names", DEFAULT_ANALYSIS_MERGE_VIEW_NAMES)
    stages["refinement"].setdefault("merge_view_names", DEFAULT_REFINEMENT_MERGE_VIEW_NAMES)

    output = {
        "include_debug": bool(include_debug),
        "include_trace": bool(include_trace),
        "include_legacy": bool(include_legacy_fields),
        "include_stage_objects": bool(include_stage_objects),
        "include_intermediate_contracts": bool(include_intermediate_contracts),
        "include_validation": True if include_validation is None else bool(include_validation),
        "schema_version": str(kwargs.get("output_schema_version") or "v2"),
    }
    artifacts: dict[str, Any] = {}
    if save_processed_dir:
        artifacts["root_dir"] = str(save_processed_dir)
    if save_processed_stages:
        artifacts["save_processed_media"] = True
        artifacts["save_processed_stages"] = list(save_processed_stages)

    overrides: dict[str, Any] = {"stages": stages, "output": output, "artifacts": artifacts}
    if model:
        overrides["model"] = {"name": model}
    return overrides


def run_vla_phase_annotation(
    client,
    video_path: str | Path | list[str | Path] | dict[str, str | Path],
    initial_instruction: str = "",
    *,
    model: str | None = None,
    robot_type: str = DEFAULT_ROBOT_TYPE,
    prompt_language: str = DEFAULT_PROMPT_LANGUAGE,
    video_id: str | None = None,
    save_processed_stages: list[str] | tuple[str, ...] | None = None,
    save_processed_dir: str | Path | None = None,
    debug: bool = False,
    include_debug: bool | None = None,
    include_trace: bool | None = None,
    include_legacy_fields: bool | None = None,
    include_intermediate_contracts: bool | None = None,
    include_validation: bool | None = None,
    include_stage_objects: bool | None = None,
    **kwargs: Any,
) -> AnnotationResult:
    """Run the configured ``scene -> analysis -> refinement`` workflow."""
    overrides = _legacy_overrides(
        model=model,
        include_debug=debug if include_debug is None else include_debug,
        include_trace=False if include_trace is None else include_trace,
        include_legacy_fields=False if include_legacy_fields is None else include_legacy_fields,
        include_stage_objects=False if include_stage_objects is None else include_stage_objects,
        include_intermediate_contracts=False
        if include_intermediate_contracts is None
        else include_intermediate_contracts,
        include_validation=True if include_validation is None else include_validation,
        save_processed_stages=save_processed_stages,
        save_processed_dir=save_processed_dir,
        kwargs=kwargs,
    )
    return run_workflow(
        client=client,
        video_path=video_path,
        instruction=initial_instruction,
        video_id=video_id,
        workflow_name="vla_phase_annotation",
        prompt_language=prompt_language,
        robot_type=robot_type,
        config_overrides=overrides,
    )
