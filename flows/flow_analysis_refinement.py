"""Single-view no-steps-raw annotation flow adapted from FineVLA.

Flow: single_view_no_steps_raw = analysis -> refinement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..utils.config import (
    DEFAULT_ANALYSIS_FPS,
    DEFAULT_ANALYSIS_MAX_TOKENS,
    DEFAULT_MAX_FRAMES,
    DEFAULT_MODEL,
    DEFAULT_PROMPT_LANGUAGE,
    DEFAULT_REFINEMENT_FPS,
    DEFAULT_REFINEMENT_MAX_TOKENS,
    DEFAULT_ROBOT_TYPE,
)
from ..utils.schemas import AnnotationResult
from ..utils.video_utils import load_video_as_image_parts
from .utils import (
    as_str_list,
    call_json_stage,
    instruction_from_steps,
    json_dumps,
    load_prompt_package,
    localize_action_sequence_objects,
    normalize_action_sequence,
    normalize_prompt_language,
    normalize_robot_type,
    translate_object_for_prompt_language,
)


def run_single_view_no_steps_raw(
    client,
    video_path: str | Path,
    initial_instruction: str,
    *,
    model: str = DEFAULT_MODEL,
    analysis_fps: float = DEFAULT_ANALYSIS_FPS,
    refinement_fps: float = DEFAULT_REFINEMENT_FPS,
    robot_type: str = DEFAULT_ROBOT_TYPE,
    prompt_language: str = DEFAULT_PROMPT_LANGUAGE,
    analysis_max_tokens: int = DEFAULT_ANALYSIS_MAX_TOKENS,
    refinement_max_tokens: int = DEFAULT_REFINEMENT_MAX_TOKENS,
    max_frames: int = DEFAULT_MAX_FRAMES,
) -> AnnotationResult:
    """Run analysis -> refinement on one main/global view."""
    robot_type = normalize_robot_type(robot_type)
    prompt_language = normalize_prompt_language(prompt_language)
    prompts = load_prompt_package(prompt_language)
    robot_type_prompt = prompts.get_robot_type_prompt(robot_type)
    analysis_parts, analysis_meta = load_video_as_image_parts(
        video_path,
        target_fps=analysis_fps,
        max_frames=max_frames,
    )
    analysis_prompt = prompts.ANALYSIS_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        robot_type=robot_type,
        action_vocabulary=prompts.ACTION_VOCABULARY,
        robot_type_prompt=robot_type_prompt,
    )
    analysis = call_json_stage(
        client,
        name="analysis",
        parts=analysis_parts,
        system_prompt=prompts.ANALYSIS_SYSTEM_PROMPT,
        user_prompt=analysis_prompt,
        model=model,
        max_tokens=analysis_max_tokens,
        fallback={"robot_type": robot_type, "action_sequence": [], "main_object": ""},
    )

    analysis.output["robot_type"] = robot_type
    action_sequence = normalize_action_sequence(analysis.output.get("action_sequence"), robot_type)
    action_sequence = localize_action_sequence_objects(action_sequence, prompt_language)
    main_object = str(analysis.output.get("main_object", "")).strip()
    main_object = translate_object_for_prompt_language(main_object, prompt_language)
    analysis.output["action_sequence"] = action_sequence
    analysis.output["main_object"] = main_object

    refinement_parts, refinement_meta = load_video_as_image_parts(
        video_path,
        target_fps=refinement_fps,
        max_frames=max_frames,
    )
    refinement_prompt = prompts.REFINEMENT_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        robot_type=robot_type,
        action_sequence=json_dumps(action_sequence),
        main_object=main_object,
        robot_type_prompt=robot_type_prompt,
        action_guidance=prompts.ACTION_FINE_GRAINED_GUIDANCE,
        FEW_SHOT_EXAMPLES=prompts.FEW_SHOT_EXAMPLES,
    )
    refinement = call_json_stage(
        client,
        name="refinement",
        parts=refinement_parts,
        system_prompt=prompts.REFINEMENT_SYSTEM_PROMPT,
        user_prompt=refinement_prompt,
        model=model,
        max_tokens=refinement_max_tokens,
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
            "robot_type": robot_type,
            "action_sequence": action_sequence,
            "main_object": main_object,
        },
        "fineGrainedSteps": steps,
        "refinedInstruction": refined_instruction,
        "metadata": {
            "prompt_language": prompt_language,
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
