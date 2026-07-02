"""Multi-view no-steps-raw annotation flow adapted from FineVLA.

Flow: multiview_no_steps_raw = analysis -> refinement -> detail_refinement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..prompts_cn import (
    DETAIL_REFINEMENT_PROMPT_TEMPLATE,
    DETAIL_REFINEMENT_SYSTEM_PROMPT,
)
from ..utils.config import DEFAULT_ANALYSIS_FPS, DEFAULT_MAX_FRAMES, DEFAULT_MODEL, DEFAULT_REFINEMENT_FPS
from ..utils.schemas import AnnotationResult
from ..utils.video_utils import labelled_view_parts, load_video_as_image_parts
from .flow_analysis_refinement import run_single_view_no_steps_raw
from .utils import as_str_list, call_json_stage, instruction_from_steps, json_dumps


def run_multiview_no_steps_raw(
    client,
    main_video_path: str | Path,
    detail_video_path: str | Path,
    initial_instruction: str,
    *,
    model: str = DEFAULT_MODEL,
    detail_view_name: str = "wrist",
    analysis_fps: float = DEFAULT_ANALYSIS_FPS,
    refinement_fps: float = DEFAULT_REFINEMENT_FPS,
    max_frames: int = DEFAULT_MAX_FRAMES,
) -> AnnotationResult:
    """Run main-view analysis/refinement, then auxiliary-view detail refinement."""
    base = run_single_view_no_steps_raw(
        client,
        main_video_path,
        initial_instruction,
        model=model,
        analysis_fps=analysis_fps,
        refinement_fps=refinement_fps,
        max_frames=max_frames,
    )

    analysis = base.stages["analysis"]
    refinement = base.stages["refinement"]
    main_object = str(analysis.output.get("main_object", "")).strip()
    previous_steps = as_str_list(refinement.output.get("fine_grained_steps"))
    previous_refined_instruction = str(
        refinement.output.get("refined_instruction", base.output.get("refinedInstruction", ""))
    ).strip()

    detail_parts, detail_meta = load_video_as_image_parts(
        detail_video_path,
        target_fps=refinement_fps,
        max_frames=max_frames,
    )
    detail_prompt = DETAIL_REFINEMENT_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        main_object=main_object,
        previous_steps=json_dumps(previous_steps),
        previous_refined_instruction=previous_refined_instruction,
    )
    detail = call_json_stage(
        client,
        name="detail_refinement",
        parts=labelled_view_parts(detail_view_name, detail_parts),
        system_prompt=DETAIL_REFINEMENT_SYSTEM_PROMPT,
        user_prompt=detail_prompt,
        model=model,
        fallback={
            "fine_grained_steps": previous_steps,
            "refined_instruction": previous_refined_instruction,
            "changes_made": [],
        },
    )

    final_steps = as_str_list(detail.output.get("fine_grained_steps")) or previous_steps
    final_instruction = str(detail.output.get("refined_instruction", "")).strip()
    if final_steps and not final_instruction:
        final_instruction = instruction_from_steps(final_steps)

    output: dict[str, Any] = {
        **base.output,
        "flow": "multiview_no_steps_raw",
        "fineGrainedSteps": final_steps,
        "refinedInstruction": final_instruction,
        "detailRefinement": {
            "changes_made": as_str_list(detail.output.get("changes_made")),
            "pre_detail_refinedInstruction": previous_refined_instruction,
            "pre_detail_fineGrainedSteps": previous_steps,
        },
        "metadata": {
            **base.output.get("metadata", {}),
            "detail_refinement": detail_meta,
        },
    }
    return AnnotationResult(
        flow_name="multiview_no_steps_raw",
        stages={
            "analysis": analysis,
            "refinement": refinement,
            "detail_refinement": detail,
        },
        output=output,
    )
