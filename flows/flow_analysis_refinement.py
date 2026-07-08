"""VLA phase annotation flow adapted from FineVLA.

Flow: vla_phase_annotation = scene -> analysis -> refinement.
"""

from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any

from ..annotation_pipeline.adapters import build_final_annotation
from ..annotation_pipeline.parsers import parse_analysis_output, parse_refinement_output, parse_scene_output
from ..utils.config import (
    DEFAULT_ANALYSIS_DRAW_TIMESTAMPS,
    DEFAULT_ANALYSIS_FPS,
    DEFAULT_ANALYSIS_INPUT_MODE,
    DEFAULT_ANALYSIS_JPEG_QUALITY,
    DEFAULT_ANALYSIS_MAX_TOKENS,
    DEFAULT_ANALYSIS_MAX_FRAMES,
    DEFAULT_ANALYSIS_MERGE_MODE,
    DEFAULT_ANALYSIS_MERGE_VIEWS,
    DEFAULT_ANALYSIS_MERGE_VIEW_NAMES,
    DEFAULT_ANALYSIS_MIN_API_FRAMES,
    DEFAULT_ANALYSIS_RESIZE_WIDTH,
    DEFAULT_MODEL,
    DEFAULT_PROMPT_LANGUAGE,
    DEFAULT_REFINEMENT_FPS,
    DEFAULT_REFINEMENT_INPUT_MODE,
    DEFAULT_REFINEMENT_JPEG_QUALITY,
    DEFAULT_REFINEMENT_MAX_TOKENS,
    DEFAULT_REFINEMENT_MAX_FRAMES,
    DEFAULT_REFINEMENT_MERGE_MODE,
    DEFAULT_REFINEMENT_MERGE_VIEWS,
    DEFAULT_REFINEMENT_MERGE_VIEW_NAMES,
    DEFAULT_REFINEMENT_MIN_API_FRAMES,
    DEFAULT_REFINEMENT_RESIZE_WIDTH,
    DEFAULT_REFINEMENT_DRAW_TIMESTAMPS,
    DEFAULT_ROBOT_TYPE,
    DEFAULT_SCENE_DRAW_TIMESTAMPS,
    DEFAULT_SCENE_FPS,
    DEFAULT_SCENE_INPUT_MODE,
    DEFAULT_SCENE_JPEG_QUALITY,
    DEFAULT_SCENE_MAX_TOKENS,
    DEFAULT_SCENE_MAX_FRAMES,
    DEFAULT_SCENE_MERGE_MODE,
    DEFAULT_SCENE_MERGE_VIEWS,
    DEFAULT_SCENE_MERGE_VIEW_NAMES,
    DEFAULT_SCENE_MIN_API_FRAMES,
    DEFAULT_SCENE_RESIZE_WIDTH,
    DEFAULT_SCENE_MERGE_LENGTH,
    DEFAULT_ANALYSIS_MERGE_LENGTH,
    DEFAULT_REFINEMENT_MERGE_LENGTH,
    DEFAULT_SCENE_DRAW_VIEWPOSITION,
    DEFAULT_ANALYSIS_DRAW_VIEWPOSITION,
    DEFAULT_REFINEMENT_DRAW_VIEWPOSITION,
    DEFAULT_SAVE_PROCESSED_DIR,
    DEFAULT_SAVE_PROCESSED_STAGES,
)
from ..utils.results import AnnotationResult
from ..utils.video_utils import load_video_or_views_as_media_parts, save_processed_media
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
    normalize_scene_context,
    normalize_timestamped_action_sequence,
    translate_object_for_prompt_language,
)


logger = logging.getLogger(__name__)


def _default_episode_name(video_path: Any, video_id: str | None) -> str:
    if video_id:
        return str(video_id)
    if isinstance(video_path, dict) and video_path:
        first_path = next(iter(video_path.values()))
        return Path(str(first_path)).stem or "episode"
    if isinstance(video_path, (list, tuple)) and video_path:
        return Path(str(video_path[0])).stem or "episode"
    return Path(str(video_path)).stem or "episode"


def _normalize_save_processed_stages(stages: list[str] | tuple[str, ...] | None) -> set[str]:
    if not stages:
        return set()
    allowed = {"scene", "analysis", "refinement"}
    normalized = {str(stage).strip() for stage in stages if str(stage).strip()}
    invalid = sorted(stage for stage in normalized if stage not in allowed)
    if invalid:
        raise ValueError(f"save_processed_stages only allows scene, analysis, refinement; invalid stage(s): {invalid}")
    return normalized


def _save_processed_stage_if_enabled(
    *,
    stage_name: str,
    parts: list[dict[str, Any]],
    save_processed_stages: set[str],
    save_processed_dir: str | Path,
    episode_name: str,
) -> None:
    if stage_name not in save_processed_stages:
        return
    if not str(save_processed_dir).strip():
        raise ValueError("save_processed_dir must be non-empty when save_processed_stages is non-empty")
    try:
        save_processed_media(
            parts,
            save_root=save_processed_dir,
            stage_name=stage_name,
            episode_name=episode_name,
        )
    except Exception as exc:
        logger.error("Save processed media failed stage=%s episode=%s error=%s", stage_name, episode_name, exc)
        raise


def run_vla_phase_annotation(
    client,
    video_path: str | Path | list[str | Path] | dict[str, str | Path],
    initial_instruction: str,
    *,
    model: str = DEFAULT_MODEL,
    scene_input_mode: str = DEFAULT_SCENE_INPUT_MODE,
    analysis_input_mode: str = DEFAULT_ANALYSIS_INPUT_MODE,
    refinement_input_mode: str = DEFAULT_REFINEMENT_INPUT_MODE,
    scene_fps: float = DEFAULT_SCENE_FPS,
    analysis_fps: float = DEFAULT_ANALYSIS_FPS,
    refinement_fps: float = DEFAULT_REFINEMENT_FPS,
    robot_type: str = DEFAULT_ROBOT_TYPE,
    prompt_language: str = DEFAULT_PROMPT_LANGUAGE,
    scene_max_tokens: int = DEFAULT_SCENE_MAX_TOKENS,
    analysis_max_tokens: int = DEFAULT_ANALYSIS_MAX_TOKENS,
    refinement_max_tokens: int = DEFAULT_REFINEMENT_MAX_TOKENS,
    scene_max_frames: int = DEFAULT_SCENE_MAX_FRAMES,
    analysis_max_frames: int = DEFAULT_ANALYSIS_MAX_FRAMES,
    refinement_max_frames: int = DEFAULT_REFINEMENT_MAX_FRAMES,
    scene_resize_width: int = DEFAULT_SCENE_RESIZE_WIDTH,
    analysis_resize_width: int = DEFAULT_ANALYSIS_RESIZE_WIDTH,
    refinement_resize_width: int = DEFAULT_REFINEMENT_RESIZE_WIDTH,
    scene_merge_view_names: list[str] | None = None,
    analysis_merge_view_names: list[str] | None = None,
    refinement_merge_view_names: list[str] | None = None,
    scene_jpeg_quality: int = DEFAULT_SCENE_JPEG_QUALITY,
    analysis_jpeg_quality: int = DEFAULT_ANALYSIS_JPEG_QUALITY,
    refinement_jpeg_quality: int = DEFAULT_REFINEMENT_JPEG_QUALITY,
    scene_min_api_frames: int = DEFAULT_SCENE_MIN_API_FRAMES,
    analysis_min_api_frames: int = DEFAULT_ANALYSIS_MIN_API_FRAMES,
    refinement_min_api_frames: int = DEFAULT_REFINEMENT_MIN_API_FRAMES,
    scene_draw_timestamps: bool = DEFAULT_SCENE_DRAW_TIMESTAMPS,
    analysis_draw_timestamps: bool = DEFAULT_ANALYSIS_DRAW_TIMESTAMPS,
    refinement_draw_timestamps: bool = DEFAULT_REFINEMENT_DRAW_TIMESTAMPS,
    scene_draw_viewposition: bool = DEFAULT_SCENE_DRAW_VIEWPOSITION,
    analysis_draw_viewposition: bool = DEFAULT_ANALYSIS_DRAW_VIEWPOSITION,
    refinement_draw_viewposition: bool = DEFAULT_REFINEMENT_DRAW_VIEWPOSITION,
    max_frames: int | None = None,
    scene_merge_views: bool = DEFAULT_SCENE_MERGE_VIEWS,
    analysis_merge_views: bool = DEFAULT_ANALYSIS_MERGE_VIEWS,
    refinement_merge_views: bool = DEFAULT_REFINEMENT_MERGE_VIEWS,
    scene_merge_mode: str = DEFAULT_SCENE_MERGE_MODE,
    analysis_merge_mode: str = DEFAULT_ANALYSIS_MERGE_MODE,
    refinement_merge_mode: str = DEFAULT_REFINEMENT_MERGE_MODE,
    scene_merge_length: int = DEFAULT_SCENE_MERGE_LENGTH,
    analysis_merge_length: int = DEFAULT_ANALYSIS_MERGE_LENGTH,
    refinement_merge_length: int = DEFAULT_REFINEMENT_MERGE_LENGTH,
    merge_views: bool | None = None,
    video_id: str | None = None,
    save_processed_stages: list[str] | tuple[str, ...] | None = None,
    save_processed_dir: str | Path = DEFAULT_SAVE_PROCESSED_DIR,
    debug: bool = False,
) -> AnnotationResult:
    """Run scene -> analysis -> refinement on one main/global view."""
    flow_start = time.perf_counter()
    robot_type = normalize_robot_type(robot_type)
    prompt_language = normalize_prompt_language(prompt_language)
    prompts = load_prompt_package(prompt_language)
    robot_type_prompt = prompts.get_robot_type_prompt(robot_type)
    if save_processed_stages is None:
        save_processed_stages = DEFAULT_SAVE_PROCESSED_STAGES
    save_processed_stage_set = _normalize_save_processed_stages(save_processed_stages)
    if save_processed_stage_set and not str(save_processed_dir).strip():
        raise ValueError("save_processed_dir must be non-empty when save_processed_stages is non-empty")
    episode_name = _default_episode_name(video_path, video_id)
    if merge_views is not None:
        scene_merge_views = merge_views
        analysis_merge_views = merge_views
        refinement_merge_views = merge_views
    if max_frames is not None:
        scene_max_frames = max_frames
        analysis_max_frames = max_frames
        refinement_max_frames = max_frames
    scene_merge_view_names = scene_merge_view_names or DEFAULT_SCENE_MERGE_VIEW_NAMES
    analysis_merge_view_names = analysis_merge_view_names or DEFAULT_ANALYSIS_MERGE_VIEW_NAMES
    refinement_merge_view_names = refinement_merge_view_names or DEFAULT_REFINEMENT_MERGE_VIEW_NAMES
    logger.info(
        "Flow vla_phase_annotation start model=%s robot_type=%s prompt_language=%s scene_fps=%s analysis_fps=%s refinement_fps=%s max_frames=%s",
        model,
        robot_type,
        prompt_language,
        scene_fps,
        analysis_fps,
        refinement_fps,
        {"scene": scene_max_frames, "analysis": analysis_max_frames, "refinement": refinement_max_frames},
    )

    step_start = time.perf_counter()
    scene_parts, scene_meta = load_video_or_views_as_media_parts(
        video_path,
        input_mode=scene_input_mode,
        target_fps=scene_fps,
        max_frames=scene_max_frames,
        resize_width=scene_resize_width,
        jpeg_quality=scene_jpeg_quality,
        draw_timestamps=scene_draw_timestamps,
        draw_viewposition=scene_draw_viewposition,
        min_api_frames=scene_min_api_frames,
        merge_length=scene_merge_length,
        merge_view_names=scene_merge_view_names,
        merge_views=scene_merge_views,
        merge_mode=scene_merge_mode,
    )
    scene_load_elapsed = time.perf_counter() - step_start
    logger.info(
        "Scene frames loaded elapsed=%.2fs sampled_frames=%s input_mode=%s selected_views=%s resize_width=%s draw_timestamps=%s",
        scene_load_elapsed,
        scene_meta.get("sampled_frames"),
        scene_meta.get("input_mode"),
        scene_meta.get("selected_views"),
        scene_resize_width,
        scene_draw_timestamps,
    )
    _save_processed_stage_if_enabled(
        stage_name="scene",
        parts=scene_parts,
        save_processed_stages=save_processed_stage_set,
        save_processed_dir=save_processed_dir,
        episode_name=episode_name,
    )
    scene_view_layout = describe_view_layout(scene_meta, prompt_language)
    scene_prompt = prompts.SCENE_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        robot_type=robot_type,
        robot_type_prompt=robot_type_prompt,
        view_layout_description=scene_view_layout,
    )
    scene = call_json_stage(
        client,
        name="scene",
        parts=scene_parts,
        system_prompt=prompts.SCENE_SYSTEM_PROMPT,
        user_prompt=scene_prompt,
        model=model,
        max_tokens=scene_max_tokens,
        fallback={"scene_context": {}},
    )
    step_start = time.perf_counter()
    scene_parse = parse_scene_output(scene.output, meta=scene_meta, video_id=video_id)
    scene_contract = scene_parse.output
    scene_context = normalize_scene_context(
        scene.output.get("sceneContext", scene.output.get("scene_context")),
        scene_meta,
    )
    if not scene_context.get("arms") and scene_contract.executors:
        scene_context["primary_view"] = scene_contract.primary_view or scene_context.get("primary_view", "unknown")
        scene_context["num_arms"] = len(scene_contract.executors)
        scene_context["arms"] = [
            {
                "arm_id": item.executor_id,
                "description": item.description,
                "spatial_reference": "primary_view",
                "main_workspace": item.main_workspace or "",
                "handled_objects": scene_contract.executor_object_map.get(item.executor_id, []),
                "best_observation_views": [
                    {"view_name": view, "reason": ""}
                    for view in item.best_observation_views
                ],
            }
            for item in scene_contract.executors
        ]
        scene_context["task_objects"] = [
            {"object_id": item.object_id, "description": item.description, "role": item.role}
            for item in scene_contract.touched_objects
        ]
        scene_context["background_objects"] = [
            {"object_id": item.object_id, "description": item.description, "role": item.role}
            for item in scene_contract.background_objects
        ]
    scene.output["sceneContext"] = scene_context
    scene.output["scene_context"] = scene_contract.model_dump(mode="json")
    scene_postprocess_elapsed = time.perf_counter() - step_start
    logger.info(
        "Scene postprocess done elapsed=%.2fs arms=%s task_objects=%s background_objects=%s",
        scene_postprocess_elapsed,
        scene_context.get("num_arms"),
        len(scene_context.get("task_objects", [])),
        len(scene_context.get("background_objects", [])),
    )

    step_start = time.perf_counter()
    analysis_parts, analysis_meta = load_video_or_views_as_media_parts(
        video_path,
        input_mode=analysis_input_mode,
        target_fps=analysis_fps,
        max_frames=analysis_max_frames,
        resize_width=analysis_resize_width,
        jpeg_quality=analysis_jpeg_quality,
        draw_timestamps=analysis_draw_timestamps,
        draw_viewposition=analysis_draw_viewposition,
        min_api_frames=analysis_min_api_frames,
        merge_length=analysis_merge_length,
        merge_view_names=analysis_merge_view_names,
        merge_views=analysis_merge_views,
        merge_mode=analysis_merge_mode,
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
    _save_processed_stage_if_enabled(
        stage_name="analysis",
        parts=analysis_parts,
        save_processed_stages=save_processed_stage_set,
        save_processed_dir=save_processed_dir,
        episode_name=episode_name,
    )
    analysis_view_layout = describe_view_layout(analysis_meta, prompt_language)
    analysis_prompt = prompts.ANALYSIS_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        robot_type=robot_type,
        action_vocabulary=prompts.ACTION_VOCABULARY,
        scene_context=json_dumps(scene_contract.model_dump(mode="json")),
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
        fallback={"candidate_segments": [], "uncertain_regions": [], "analysis_notes": []},
    )

    step_start = time.perf_counter()
    analysis.output["robot_type"] = robot_type
    analysis_parse = parse_analysis_output(analysis.output, scene=scene_contract, video_id=video_id)
    analysis_contract = analysis_parse.output
    action_sequence = normalize_action_sequence(analysis.output.get("action_sequence"), robot_type)
    if not action_sequence:
        action_sequence = [
            {
                "executor": segment.executor,
                "action": segment.action,
                "object": segment.objects[0] if segment.objects else "",
            }
            for segment in analysis_contract.candidate_segments
        ]
    action_sequence = localize_action_sequence_objects(action_sequence, prompt_language)
    main_object = str(analysis.output.get("main_object", "")).strip()
    if not main_object:
        for segment in analysis_contract.candidate_segments:
            if segment.objects:
                main_object = segment.objects[0]
                break
    main_object = translate_object_for_prompt_language(main_object, prompt_language)
    analysis.output["action_sequence"] = action_sequence
    analysis.output["candidate_segments"] = analysis_contract.model_dump(mode="json")["candidate_segments"]
    analysis.output["main_object"] = main_object
    analysis_postprocess_elapsed = time.perf_counter() - step_start
    logger.info(
        "Analysis postprocess done elapsed=%.2fs actions=%s main_object=%s",
        analysis_postprocess_elapsed,
        len(action_sequence),
        main_object,
    )

    step_start = time.perf_counter()
    refinement_parts, refinement_meta = load_video_or_views_as_media_parts(
        video_path,
        input_mode=refinement_input_mode,
        target_fps=refinement_fps,
        max_frames=refinement_max_frames,
        resize_width=refinement_resize_width,
        jpeg_quality=refinement_jpeg_quality,
        draw_timestamps=refinement_draw_timestamps,
        draw_viewposition=refinement_draw_viewposition,
        min_api_frames=refinement_min_api_frames,
        merge_length=refinement_merge_length,
        merge_view_names=refinement_merge_view_names,
        merge_views=refinement_merge_views,
        merge_mode=refinement_merge_mode,
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
    _save_processed_stage_if_enabled(
        stage_name="refinement",
        parts=refinement_parts,
        save_processed_stages=save_processed_stage_set,
        save_processed_dir=save_processed_dir,
        episode_name=episode_name,
    )
    refinement_view_layout = describe_view_layout(refinement_meta, prompt_language)
    refinement_prompt = prompts.REFINEMENT_PROMPT_TEMPLATE.format(
        initial_instruction=initial_instruction,
        robot_type=robot_type,
        action_sequence=json_dumps(
            [segment.model_dump(mode="json") for segment in analysis_contract.candidate_segments]
        ),
        main_object=main_object,
        scene_context=json_dumps(scene_contract.model_dump(mode="json")),
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
        fallback={"refined_segments": [], "changes": []},
    )

    step_start = time.perf_counter()
    refinement_parse = parse_refinement_output(
        refinement.output,
        analysis=analysis_contract,
        scene=scene_contract,
        video_id=video_id,
    )
    refinement_contract = refinement_parse.output
    timestamped_actions = normalize_timestamped_action_sequence(
        refinement.output.get("timestamped_action_sequence"),
        action_sequence,
        robot_type,
    )
    if not timestamped_actions:
        timestamped_actions = [
            {
                "executor": segment.executor,
                "action": segment.action,
                "object": segment.objects[0] if segment.objects else "",
                "start_time": segment.start_time or "",
                "end_time": segment.end_time or "",
            }
            for segment in refinement_contract.refined_segments
        ]
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
    logger.info("Flow vla_phase_annotation done elapsed=%.2fs", total_elapsed)

    validation_warnings = [
        *scene_parse.warnings,
        *scene_parse.errors,
        *analysis_parse.warnings,
        *analysis_parse.errors,
        *refinement_parse.warnings,
        *refinement_parse.errors,
    ]
    for warning in validation_warnings:
        logger.warning("Contract validation: %s", warning)

    final_annotation = build_final_annotation(
        scene=scene_contract,
        refinement=refinement_contract,
        video_id=video_id,
        model=model,
        flow_name="vla_phase_annotation",
    )
    output: dict[str, Any] = {
        **final_annotation.model_dump(mode="json"),
        "scene_context": scene_contract.model_dump(mode="json"),
        "candidate_segments": analysis_contract.model_dump(mode="json")["candidate_segments"],
        "refined_segments": refinement_contract.model_dump(mode="json")["refined_segments"],
        "changes": refinement_contract.model_dump(mode="json")["changes"],
        "validation_warnings": validation_warnings,
        "metadata": {
            **final_annotation.metadata,
            "prompt_language": prompt_language,
            "robot_type": robot_type,
            "elapsed_seconds": round(total_elapsed, 3),
        },
    }
    if debug:
        output["debug"] = {
            "initial_instruction": initial_instruction,
            "legacy": {
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
            "stage_metadata": {
                "scene": {
                    **scene_meta,
                    "load_elapsed_seconds": round(scene_load_elapsed, 3),
                    "postprocess_elapsed_seconds": round(scene_postprocess_elapsed, 3),
                },
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
            },
        }
    return AnnotationResult(
        flow_name="vla_phase_annotation",
        stages={"scene": scene, "analysis": analysis, "refinement": refinement},
        output=output,
    )

