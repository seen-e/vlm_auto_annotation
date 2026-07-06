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
    normalize_action_sequence,
    normalize_phase_segments,
    normalize_prompt_language,
    normalize_robot_type,
    normalize_scene,
    normalize_timestamped_action_sequence,
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
    logger.debug(
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
    logger.info("Analysis frame_loading elapsed=%.2fs", analysis_load_elapsed)
    logger.debug(
        "Analysis frame_loading details sampled_frames=%s input_mode=%s selected_views=%s resize_width=%s draw_timestamps=%s",
        analysis_meta.get("sampled_frames"),
        analysis_meta.get("input_mode"),
        analysis_meta.get("selected_views"),
        analysis_resize_width,
        analysis_draw_timestamps,
    )
    analysis_view_layout = describe_view_layout(analysis_meta, prompt_language)
    analysis_scene_prompt = prompts.ANALYSIS_SCENE_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        robot_type=robot_type,
        action_vocabulary=prompts.ACTION_VOCABULARY,
        robot_type_prompt=robot_type_prompt,
        view_layout_description=analysis_view_layout,
    )
    analysis_scene = call_json_stage(
        client,
        name="analysis_scene",
        parts=analysis_parts,
        system_prompt=prompts.ANALYSIS_SCENE_SYSTEM_PROMPT,
        user_prompt=analysis_scene_prompt,
        model=model,
        max_tokens=analysis_max_tokens,
        fallback={"scene": {"robot_type": robot_type, "arms": [], "objects": []}, "main_object": None},
    )

    step_start = time.perf_counter()
    scene = normalize_scene(analysis_scene.output.get("scene"), robot_type, [])
    main_object = str(analysis_scene.output.get("main_object") or "").strip()
    if not main_object and scene["objects"]:
        main_object = scene["objects"][0]["object_id"]
    analysis_scene.output["scene"] = scene
    analysis_scene.output["main_object"] = main_object
    analysis_scene_seed = {
        "scene": scene,
        "main_object": main_object,
    }

    analysis_events_prompt = prompts.ANALYSIS_EVENTS_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        robot_type=robot_type,
        analysis_scene=json_dumps(analysis_scene_seed),
        action_vocabulary=prompts.ACTION_VOCABULARY,
        robot_type_prompt=robot_type_prompt,
        view_layout_description=analysis_view_layout,
    )
    analysis_events = call_json_stage(
        client,
        name="analysis_events",
        parts=analysis_parts,
        system_prompt=prompts.ANALYSIS_EVENTS_SYSTEM_PROMPT,
        user_prompt=analysis_events_prompt,
        model=model,
        max_tokens=analysis_max_tokens,
        fallback={"action_sequence": []},
    )

    action_sequence = normalize_action_sequence(analysis_events.output.get("action_sequence"), robot_type)
    scene = normalize_scene(scene, robot_type, action_sequence)
    analysis_scene.output["scene"] = scene
    analysis_events.output["action_sequence"] = action_sequence
    analysis_result = {
        "robot_type": robot_type,
        "scene": scene,
        "main_object": main_object,
        "action_sequence": action_sequence,
    }
    analysis_postprocess_elapsed = time.perf_counter() - step_start
    logger.info("Analysis postprocess elapsed=%.2fs", analysis_postprocess_elapsed)
    logger.debug("Analysis postprocess details actions=%s main_object=%s", len(action_sequence), main_object)

    step_start = time.perf_counter()
    refinement_parts, refinement_meta = load_video_or_views_as_image_parts(
        video_path,
        target_fps=refinement_fps,
        max_frames=max_frames,
        resize_width=refinement_resize_width,
        draw_timestamps=refinement_draw_timestamps,
    )
    refinement_load_elapsed = time.perf_counter() - step_start
    logger.info("Refinement frame_loading elapsed=%.2fs", refinement_load_elapsed)
    logger.debug(
        "Refinement frame_loading details sampled_frames=%s input_mode=%s selected_views=%s resize_width=%s draw_timestamps=%s",
        refinement_meta.get("sampled_frames"),
        refinement_meta.get("input_mode"),
        refinement_meta.get("selected_views"),
        refinement_resize_width,
        refinement_draw_timestamps,
    )
    refinement_view_layout = describe_view_layout(refinement_meta, prompt_language)
    refinement_phases_prompt = prompts.REFINEMENT_PHASES_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        robot_type=robot_type,
        analysis_result=json_dumps(analysis_result),
        robot_type_prompt=robot_type_prompt,
        view_layout_description=refinement_view_layout,
        action_guidance=prompts.ACTION_FINE_GRAINED_GUIDANCE,
        FEW_SHOT_EXAMPLES=prompts.FEW_SHOT_EXAMPLES,
    )
    refinement_phases = call_json_stage(
        client,
        name="refinement_phases",
        parts=refinement_parts,
        system_prompt=prompts.REFINEMENT_PHASES_SYSTEM_PROMPT,
        user_prompt=refinement_phases_prompt,
        model=model,
        max_tokens=refinement_max_tokens,
        fallback={"phaseSegments": []},
    )
    semantic_phase_segments = normalize_phase_segments(
        refinement_phases.output.get("phaseSegments", refinement_phases.output.get("phase_segments")),
        [],
        robot_type,
        is_single_view=refinement_meta.get("input_mode") == "single_view",
        fallback_actions=action_sequence,
    )
    refinement_phases.output["phaseSegments"] = semantic_phase_segments

    refinement_boundaries_prompt = prompts.REFINEMENT_BOUNDARIES_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        robot_type=robot_type,
        analysis_result=json_dumps(analysis_result),
        phase_segments=json_dumps(semantic_phase_segments),
        robot_type_prompt=robot_type_prompt,
        view_layout_description=refinement_view_layout,
    )
    refinement_boundaries = call_json_stage(
        client,
        name="refinement_boundaries",
        parts=refinement_parts,
        system_prompt=prompts.REFINEMENT_BOUNDARIES_SYSTEM_PROMPT,
        user_prompt=refinement_boundaries_prompt,
        model=model,
        max_tokens=refinement_max_tokens,
        fallback={
            "timestamped_action_sequence": [],
            "phaseSegments": semantic_phase_segments,
            "fine_grained_steps": [],
            "refined_instruction": "",
        },
    )

    step_start = time.perf_counter()
    timestamped_actions = normalize_timestamped_action_sequence(
        refinement_boundaries.output.get("timestamped_action_sequence", refinement_boundaries.output.get("timestampedActionSequence")),
        action_sequence,
        robot_type,
    )
    phase_segments = normalize_phase_segments(
        refinement_boundaries.output.get("phaseSegments", refinement_boundaries.output.get("phase_segments")),
        timestamped_actions,
        robot_type,
        is_single_view=refinement_meta.get("input_mode") == "single_view",
        fallback_actions=semantic_phase_segments or action_sequence,
    )
    if not timestamped_actions and phase_segments:
        timestamped_actions = [
            {
                "event_id": phase.get("source_event_id"),
                "executor": phase.get("executor"),
                "action": phase.get("action"),
                "object": phase.get("object"),
                "target": phase.get("target"),
                "start_time": phase.get("start_time", ""),
                "end_time": phase.get("end_time", ""),
            }
            for phase in phase_segments
        ]
    refinement_boundaries.output["timestamped_action_sequence"] = timestamped_actions
    refinement_boundaries.output["phaseSegments"] = phase_segments
    steps = as_str_list(refinement_boundaries.output.get("fine_grained_steps"))
    refined_instruction = str(refinement_boundaries.output.get("refined_instruction", "")).strip()
    if steps and not refined_instruction:
        refined_instruction = instruction_from_steps(steps)
    refinement_postprocess_elapsed = time.perf_counter() - step_start
    total_elapsed = time.perf_counter() - flow_start
    logger.info("Refinement postprocess elapsed=%.2fs", refinement_postprocess_elapsed)
    logger.debug(
        "Refinement postprocess details timestamped_actions=%s phase_segments=%s fine_grained_steps=%s",
        len(timestamped_actions),
        len(phase_segments),
        len(steps),
    )
    logger.info("Flow single_view_no_steps_raw elapsed=%.2fs", total_elapsed)

    output: dict[str, Any] = {
        "flow": "single_view_no_steps_raw",
        "initialInstruction": initial_instruction,
        "analysisResult": analysis_result,
        "timestampedActionSequence": timestamped_actions,
        "phaseSegments": phase_segments,
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
        stages={
            "analysis_scene": analysis_scene,
            "analysis_events": analysis_events,
            "refinement_phases": refinement_phases,
            "refinement_boundaries": refinement_boundaries,
        },
        output=output,
    )


# Backward-compatible alias for older callers.
run_standard_two_stage = run_single_view_no_steps_raw
