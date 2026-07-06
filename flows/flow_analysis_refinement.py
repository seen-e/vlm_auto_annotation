"""Single-view no-steps-raw annotation flow adapted from FineVLA.

Flow: single_view_no_steps_raw = analysis -> refinement.
"""

from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any

from ..utils.config import (
    DEFAULT_ANALYSIS_DRAW_TIMESTAMPS,
    DEFAULT_ANALYSIS_FPS,
    DEFAULT_ANALYSIS_MAX_TOKENS,
    DEFAULT_ANALYSIS_RESIZE_WIDTH,
    DEFAULT_MAX_FRAMES,
    DEFAULT_MODEL,
    DEFAULT_PROMPT_LANGUAGE,
    DEFAULT_REFINEMENT_FPS,
    DEFAULT_REFINEMENT_MAX_TOKENS,
    DEFAULT_REFINEMENT_RESIZE_WIDTH,
    DEFAULT_REFINEMENT_DRAW_TIMESTAMPS,
    DEFAULT_ROBOT_TYPE,
)
from ..utils.schemas import AnnotationResult
from ..utils.video_utils import load_video_or_views_as_image_parts
from .utils import (
    as_str_list,
    call_json_stage,
    describe_view_layout,
    instruction_from_steps,
    json_dumps,
    load_prompt_package,
    localize_action_sequence_objects,
    normalize_action_sequence,
    normalize_prompt_language,
    normalize_robot_type,
    normalize_timestamped_action_sequence,
    translate_object_for_prompt_language,
)


logger = logging.getLogger(__name__)


def run_single_view_no_steps_raw(
    client,
    video_path: str | Path | list[str | Path] | dict[str, str | Path],
    initial_instruction: str,
    *,
    model: str = DEFAULT_MODEL,
    analysis_fps: float = DEFAULT_ANALYSIS_FPS,
    refinement_fps: float = DEFAULT_REFINEMENT_FPS,
    robot_type: str = DEFAULT_ROBOT_TYPE,
    prompt_language: str = DEFAULT_PROMPT_LANGUAGE,
    analysis_max_tokens: int = DEFAULT_ANALYSIS_MAX_TOKENS,
    refinement_max_tokens: int = DEFAULT_REFINEMENT_MAX_TOKENS,
    analysis_resize_width: int = DEFAULT_ANALYSIS_RESIZE_WIDTH,
    refinement_resize_width: int = DEFAULT_REFINEMENT_RESIZE_WIDTH,
    analysis_draw_timestamps: bool = DEFAULT_ANALYSIS_DRAW_TIMESTAMPS,
    refinement_draw_timestamps: bool = DEFAULT_REFINEMENT_DRAW_TIMESTAMPS,
    max_frames: int = DEFAULT_MAX_FRAMES,
) -> AnnotationResult:
    """Run analysis -> refinement on one main/global view."""
    flow_start = time.perf_counter()
    robot_type = normalize_robot_type(robot_type)
    prompt_language = normalize_prompt_language(prompt_language)
    logger.info(
        "Flow single_view_no_steps_raw start model=%s robot_type=%s prompt_language=%s analysis_fps=%s refinement_fps=%s max_frames=%s",
        model,
        robot_type,
        prompt_language,
        analysis_fps,
        refinement_fps,
        max_frames,
    )
    prompts = load_prompt_package(prompt_language)
    robot_type_prompt = prompts.get_robot_type_prompt(robot_type)
    step_start = time.perf_counter()
    analysis_parts, analysis_meta = load_video_or_views_as_image_parts(
        video_path,
        target_fps=analysis_fps,
        max_frames=max_frames,
        resize_width=analysis_resize_width,
        draw_timestamps=analysis_draw_timestamps,
    )
    analysis_load_elapsed = time.perf_counter() - step_start
    logger.info(
        "Analysis frames loaded elapsed=%.2fs sampled_frames=%s input_mode=%s selected_views=%s resize_width=%s draw_timestamps=%s",
        analysis_load_elapsed,
        analysis_meta.get("sampled_frames"),
        analysis_meta.get("input_mode"),
        analysis_meta.get("selected_views"),
        analysis_resize_width,
        analysis_draw_timestamps,
    )
    analysis_view_layout = describe_view_layout(analysis_meta, prompt_language)
    analysis_prompt = prompts.ANALYSIS_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        robot_type=robot_type,
        action_vocabulary=prompts.ACTION_VOCABULARY,
        robot_type_prompt=robot_type_prompt,
        view_layout_description=analysis_view_layout,
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

    step_start = time.perf_counter()
    analysis.output["robot_type"] = robot_type
    action_sequence = normalize_action_sequence(analysis.output.get("action_sequence"), robot_type)
    action_sequence = localize_action_sequence_objects(action_sequence, prompt_language)
    main_object = str(analysis.output.get("main_object", "")).strip()
    main_object = translate_object_for_prompt_language(main_object, prompt_language)
    analysis.output["action_sequence"] = action_sequence
    analysis.output["main_object"] = main_object
    analysis_postprocess_elapsed = time.perf_counter() - step_start
    logger.info(
        "Analysis postprocess done elapsed=%.2fs actions=%s main_object=%s",
        analysis_postprocess_elapsed,
        len(action_sequence),
        main_object,
    )

    step_start = time.perf_counter()
    refinement_parts, refinement_meta = load_video_or_views_as_image_parts(
        video_path,
        target_fps=refinement_fps,
        max_frames=max_frames,
        resize_width=refinement_resize_width,
        draw_timestamps=refinement_draw_timestamps,
    )
    refinement_load_elapsed = time.perf_counter() - step_start
    logger.info(
        "Refinement frames loaded elapsed=%.2fs sampled_frames=%s input_mode=%s selected_views=%s resize_width=%s draw_timestamps=%s",
        refinement_load_elapsed,
        refinement_meta.get("sampled_frames"),
        refinement_meta.get("input_mode"),
        refinement_meta.get("selected_views"),
        refinement_resize_width,
        refinement_draw_timestamps,
    )
    refinement_view_layout = describe_view_layout(refinement_meta, prompt_language)
    refinement_prompt = prompts.REFINEMENT_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        robot_type=robot_type,
        action_sequence=json_dumps(action_sequence),
        main_object=main_object,
        robot_type_prompt=robot_type_prompt,
        view_layout_description=refinement_view_layout,
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
        fallback={"timestamped_action_sequence": [], "fine_grained_steps": [], "refined_instruction": ""},
    )

    step_start = time.perf_counter()
    timestamped_actions = normalize_timestamped_action_sequence(
        refinement.output.get("timestamped_action_sequence"),
        action_sequence,
        robot_type,
    )
    timestamped_actions = localize_action_sequence_objects(timestamped_actions, prompt_language)
    steps = as_str_list(refinement.output.get("fine_grained_steps"))
    refined_instruction = str(refinement.output.get("refined_instruction", "")).strip()
    if steps and not refined_instruction:
        refined_instruction = instruction_from_steps(steps)
    refinement_postprocess_elapsed = time.perf_counter() - step_start
    total_elapsed = time.perf_counter() - flow_start
    logger.info(
        "Refinement postprocess done elapsed=%.2fs timestamped_actions=%s fine_grained_steps=%s",
        refinement_postprocess_elapsed,
        len(timestamped_actions),
        len(steps),
    )
    logger.info("Flow single_view_no_steps_raw done elapsed=%.2fs", total_elapsed)

    output: dict[str, Any] = {
        "flow": "single_view_no_steps_raw",
        "initialInstruction": initial_instruction,
        "analysisResult": {
            "robot_type": robot_type,
            "action_sequence": action_sequence,
            "main_object": main_object,
        },
        "timestampedActionSequence": timestamped_actions,
        "fineGrainedSteps": steps,
        "refinedInstruction": refined_instruction,
        "metadata": {
            "prompt_language": prompt_language,
            "analysis": {
                **analysis_meta,
                "load_elapsed_seconds": round(analysis_load_elapsed, 3),
                "postprocess_elapsed_seconds": round(analysis_postprocess_elapsed, 3),
            },
            "refinement": {
                **refinement_meta,
                "load_elapsed_seconds": round(refinement_load_elapsed, 3),
                "postprocess_elapsed_seconds": round(refinement_postprocess_elapsed, 3),
            },
            "elapsed_seconds": round(total_elapsed, 3),
        },
    }
    return AnnotationResult(
        flow_name="single_view_no_steps_raw",
        stages={"analysis": analysis, "refinement": refinement},
        output=output,
    )


# Backward-compatible alias for older callers.
run_standard_two_stage = run_single_view_no_steps_raw
