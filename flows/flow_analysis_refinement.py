"""Single-view no-steps-raw annotation flow adapted from FineVLA.

Flow: single_view_no_steps_raw = analysis -> refinement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..prompts_cn import (
    ACTION_FINE_GRAINED_GUIDANCE,
    ACTION_VOCABULARY,
    ANALYSIS_PROMPT_TEMPLATE,
    ANALYSIS_SYSTEM_PROMPT,
    FEW_SHOT_EXAMPLES,
    REFINEMENT_PROMPT_TEMPLATE,
    REFINEMENT_SYSTEM_PROMPT,
)
from ..utils.config import DEFAULT_ANALYSIS_FPS, DEFAULT_MAX_FRAMES, DEFAULT_MODEL, DEFAULT_REFINEMENT_FPS
from ..utils.schemas import AnnotationResult
from ..utils.video_utils import load_video_as_image_parts
from .utils import as_str_list, call_json_stage, instruction_from_steps


def run_single_view_no_steps_raw(
    client,
    video_path: str | Path,
    initial_instruction: str,
    *,
    model: str = DEFAULT_MODEL,
    analysis_fps: float = DEFAULT_ANALYSIS_FPS,
    refinement_fps: float = DEFAULT_REFINEMENT_FPS,
    max_frames: int = DEFAULT_MAX_FRAMES,
) -> AnnotationResult:
    """Run analysis -> refinement on one main/global view."""
    analysis_parts, analysis_meta = load_video_as_image_parts(
        video_path,
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
        video_path,
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
        name="refinement",
        parts=refinement_parts,
        system_prompt=REFINEMENT_SYSTEM_PROMPT,
        user_prompt=refinement_prompt,
        model=model,
        fallback={"fine_grained_steps": [], "refined_instruction": ""},
    )

    steps = as_str_list(refinement.output.get("fine_grained_steps"))
    refined_instruction = str(refinement.output.get("refined_instruction", "")).strip()
    if steps and not refined_instruction:
        refined_instruction = instruction_from_steps(steps)

    output: dict[str, Any] = {
        "flow": "single_view_no_steps_raw",
        "initialInstruction": initial_instruction,
        "analysisResult": {
            "action_sequence": action_sequence,
            "main_object": main_object,
        },
        "fineGrainedSteps": steps,
        "refinedInstruction": refined_instruction,
        "metadata": {
            "analysis": analysis_meta,
            "refinement": refinement_meta,
        },
    }
    return AnnotationResult(
        flow_name="single_view_no_steps_raw",
        stages={"analysis": analysis, "refinement": refinement},
        output=output,
    )


# Backward-compatible alias for older callers.
run_standard_two_stage = run_single_view_no_steps_raw
