"""Flow 02: FineVLA multi-view three-stage annotation.

Use this when a task has a global/main view and one close-up detail view but no
pre-segmented ``steps_raw``. It mirrors analysis -> refinement -> detail polish.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import DEFAULT_ANALYSIS_FPS, DEFAULT_MAX_FRAMES, DEFAULT_MODEL, DEFAULT_REFINEMENT_FPS
from ..prompts_cn import (
    ACTION_FINE_GRAINED_GUIDANCE,
    ACTION_VOCABULARY,
    ANALYSIS_PROMPT_TEMPLATE,
    ANALYSIS_SYSTEM_PROMPT,
    DETAIL_REFINEMENT_PROMPT_TEMPLATE,
    DETAIL_REFINEMENT_SYSTEM_PROMPT,
    FEW_SHOT_EXAMPLES,
    REFINEMENT_PROMPT_TEMPLATE,
    REFINEMENT_SYSTEM_PROMPT,
)
from ..schemas import AnnotationResult
from ..video_utils import labelled_view_parts, load_video_as_image_parts
from .utils import as_str_list, call_json_stage, instruction_from_steps, json_dumps


def run_multiview_three_stage(
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
    """Run main-view analysis/refinement and close-view correction."""
    analysis_parts, analysis_meta = load_video_as_image_parts(
        main_video_path,
        target_fps=analysis_fps,
        max_frames=max_frames,
    )
    analysis_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        action_vocabulary=ACTION_VOCABULARY,
    )
    analysis = call_json_stage(
        client,
        name="analysis",
        parts=analysis_parts,
        system_prompt=ANALYSIS_SYSTEM_PROMPT,
        user_prompt=analysis_prompt,
        model=model,
        fallback={"action_sequence": [], "main_object": ""},
    )

    action_sequence = as_str_list(analysis.output.get("action_sequence"))
    main_object = str(analysis.output.get("main_object", "")).strip()

    refinement_parts, refinement_meta = load_video_as_image_parts(
        main_video_path,
        target_fps=refinement_fps,
        max_frames=max_frames,
    )
    refinement_prompt = REFINEMENT_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        action_sequence=action_sequence,
        main_object=main_object,
        action_guidance=ACTION_FINE_GRAINED_GUIDANCE,
        FEW_SHOT_EXAMPLES=FEW_SHOT_EXAMPLES,
    )
    refinement = call_json_stage(
        client,
        name="main_refinement",
        parts=refinement_parts,
        system_prompt=REFINEMENT_SYSTEM_PROMPT,
        user_prompt=refinement_prompt,
        model=model,
        fallback={"fine_grained_steps": [], "refined_instruction": ""},
    )

    main_steps = as_str_list(refinement.output.get("fine_grained_steps"))
    main_refined_instruction = str(refinement.output.get("refined_instruction", "")).strip()
    if main_steps and not main_refined_instruction:
        main_refined_instruction = instruction_from_steps(main_steps)

    detail_parts, detail_meta = load_video_as_image_parts(
        detail_video_path,
        target_fps=refinement_fps,
        max_frames=max_frames,
    )
    detail_prompt = DETAIL_REFINEMENT_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        main_object=main_object,
        previous_steps=json_dumps(main_steps),
        previous_refined_instruction=main_refined_instruction,
    )
    detail = call_json_stage(
        client,
        name="detail_refinement",
        parts=labelled_view_parts(detail_view_name, detail_parts),
        system_prompt=DETAIL_REFINEMENT_SYSTEM_PROMPT,
        user_prompt=detail_prompt,
        model=model,
        fallback={
            "fine_grained_steps": main_steps,
            "refined_instruction": main_refined_instruction,
            "changes_made": [],
        },
    )

    final_steps = as_str_list(detail.output.get("fine_grained_steps")) or main_steps
    final_instruction = str(detail.output.get("refined_instruction", "")).strip()
    if final_steps and not final_instruction:
        final_instruction = instruction_from_steps(final_steps)

    output: dict[str, Any] = {
        "flow": "multiview_three_stage",
        "initialInstruction": initial_instruction,
        "analysisResult": {
            "action_sequence": action_sequence,
            "main_object": main_object,
        },
        "mainViewSteps": main_steps,
        "fineGrainedSteps": final_steps,
        "refinedInstruction": final_instruction,
        "detailChanges": as_str_list(detail.output.get("changes_made")),
        "metadata": {
            "analysis": analysis_meta,
            "main_refinement": refinement_meta,
            "detail_refinement": detail_meta,
        },
    }
    return AnnotationResult(
        flow_name="flow_02_multiview_three_stage",
        stages={
            "analysis": analysis,
            "main_refinement": refinement,
            "detail_refinement": detail,
        },
        output=output,
    )
