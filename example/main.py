r"""Run VLA phase annotation on one video or a JSON batch.

Single video:

    python C:\Users\34927\Desktop\embodiflow-agent\vlm_auto_annotation\example\main.py ^
        --main-video C:\path\to\main.mp4 ^
        --instruction "pick up the cup and place it on the plate"

Batch JSON:

    python C:\Users\34927\Desktop\embodiflow-agent\vlm_auto_annotation\example\main.py ^
        --input-json C:\path\to\input.json ^
        --output-json C:\path\to\predictions.json

Default batch:

    python C:\Users\34927\Desktop\embodiflow-agent\vlm_auto_annotation\example\main.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# This example lives inside the package directory. Add the repository root so
# `import vlm_auto_annotation` works even when the package is not installed.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EXAMPLE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_JSON = EXAMPLE_DIR / "robot_mind2_camera_top_tasks.json"
DEFAULT_OUTPUT_JSON = EXAMPLE_DIR / "Qwen3.5-27B-bf16.json"

from vlm_auto_annotation import create_openai_client
from vlm_auto_annotation.flows import run_vla_phase_annotation
from vlm_auto_annotation.utils.logging_utils import configure_logging
from vlm_auto_annotation.utils.config import (
    DEFAULT_API_KEY,
    DEFAULT_ANALYSIS_DRAW_TIMESTAMPS,
    DEFAULT_ANALYSIS_FPS,
    DEFAULT_ANALYSIS_INPUT_MODE,
    DEFAULT_ANALYSIS_JPEG_QUALITY,
    DEFAULT_ANALYSIS_MAX_FRAMES,
    DEFAULT_ANALYSIS_MAX_TOKENS,
    DEFAULT_ANALYSIS_MERGE_MODE,
    DEFAULT_ANALYSIS_MERGE_VIEW_NAMES,
    DEFAULT_ANALYSIS_MERGE_VIEWS,
    DEFAULT_ANALYSIS_MIN_API_FRAMES,
    DEFAULT_ANALYSIS_RESIZE_WIDTH,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_PROMPT_LANGUAGE,
    DEFAULT_REFINEMENT_FPS,
    DEFAULT_REFINEMENT_INPUT_MODE,
    DEFAULT_REFINEMENT_JPEG_QUALITY,
    DEFAULT_REFINEMENT_MAX_FRAMES,
    DEFAULT_REFINEMENT_MAX_TOKENS,
    DEFAULT_REFINEMENT_MERGE_MODE,
    DEFAULT_REFINEMENT_MERGE_VIEW_NAMES,
    DEFAULT_REFINEMENT_MERGE_VIEWS,
    DEFAULT_REFINEMENT_MIN_API_FRAMES,
    DEFAULT_REFINEMENT_DRAW_TIMESTAMPS,
    DEFAULT_REFINEMENT_RESIZE_WIDTH,
    DEFAULT_ROBOT_TYPE,
    DEFAULT_SCENE_DRAW_TIMESTAMPS,
    DEFAULT_SCENE_DRAW_VIEWPOSITION,
    DEFAULT_ANALYSIS_DRAW_VIEWPOSITION,
    DEFAULT_REFINEMENT_DRAW_VIEWPOSITION,
    DEFAULT_SAVE_PROCESSED_DIR,
    DEFAULT_SAVE_PROCESSED_STAGES,
    DEFAULT_SCENE_FPS,
    DEFAULT_SCENE_INPUT_MODE,
    DEFAULT_SCENE_JPEG_QUALITY,
    DEFAULT_SCENE_MAX_FRAMES,
    DEFAULT_SCENE_MAX_TOKENS,
    DEFAULT_SCENE_MERGE_MODE,
    DEFAULT_SCENE_MERGE_VIEW_NAMES,
    DEFAULT_SCENE_MERGE_VIEWS,
    DEFAULT_SCENE_MIN_API_FRAMES,
    DEFAULT_SCENE_RESIZE_WIDTH,
    DEFAULT_SCENE_MERGE_LENGTH,
    DEFAULT_ANALYSIS_MERGE_LENGTH,
    DEFAULT_REFINEMENT_MERGE_LENGTH,
)


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run VLA phase annotation.")
    parser.add_argument(
        "--input-json",
        default=str(DEFAULT_INPUT_JSON),
        help=f"Batch input JSON file. Default: {DEFAULT_INPUT_JSON}",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help=f"Where to save merged batch prediction results. Default: {DEFAULT_OUTPUT_JSON}",
    )
    parser.add_argument("--main-video", help="Path to the main/global view video for single-video mode.")
    parser.add_argument(
        "--instruction",
        help="Initial task instruction, for example: 'pick up the cup and place it on the plate'.",
    )
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", DEFAULT_API_KEY))
    parser.add_argument("--base-url", default=os.environ.get("ANNOTATE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--model", default=os.environ.get("ANNOTATE_MODEL", DEFAULT_MODEL))
    parser.add_argument(
        "--robot-type",
        default=DEFAULT_ROBOT_TYPE,
        choices=["single_arm", "bimanual", "mobile_manipulator", "unknown"],
        help="Configured robot type used by all VLM stages.",
    )
    parser.add_argument(
        "--prompt-language",
        default=DEFAULT_PROMPT_LANGUAGE,
        choices=["cn", "en"],
        help="Prompt language: cn uses prompts/prompts_cn, en uses prompts/prompts_en.",
    )
    parser.add_argument("--scene-fps", type=float, default=DEFAULT_SCENE_FPS)
    parser.add_argument("--analysis-fps", type=float, default=DEFAULT_ANALYSIS_FPS)
    parser.add_argument("--refinement-fps", type=float, default=DEFAULT_REFINEMENT_FPS)
    parser.add_argument("--scene-input-mode", choices=["image_sequence", "video"], default=DEFAULT_SCENE_INPUT_MODE)
    parser.add_argument("--analysis-input-mode", choices=["image_sequence", "video"], default=DEFAULT_ANALYSIS_INPUT_MODE)
    parser.add_argument("--refinement-input-mode", choices=["image_sequence", "video"], default=DEFAULT_REFINEMENT_INPUT_MODE)
    parser.add_argument("--scene-max-tokens", type=int, default=DEFAULT_SCENE_MAX_TOKENS)
    parser.add_argument("--analysis-max-tokens", type=int, default=DEFAULT_ANALYSIS_MAX_TOKENS)
    parser.add_argument("--refinement-max-tokens", type=int, default=DEFAULT_REFINEMENT_MAX_TOKENS)
    parser.add_argument("--scene-resize-width", type=int, default=DEFAULT_SCENE_RESIZE_WIDTH)
    parser.add_argument("--analysis-resize-width", type=int, default=DEFAULT_ANALYSIS_RESIZE_WIDTH)
    parser.add_argument("--refinement-resize-width", type=int, default=DEFAULT_REFINEMENT_RESIZE_WIDTH)
    parser.add_argument("--scene-max-frames", type=int, default=DEFAULT_SCENE_MAX_FRAMES)
    parser.add_argument("--analysis-max-frames", type=int, default=DEFAULT_ANALYSIS_MAX_FRAMES)
    parser.add_argument("--refinement-max-frames", type=int, default=DEFAULT_REFINEMENT_MAX_FRAMES)
    parser.add_argument("--scene-merge-view-names", default=",".join(DEFAULT_SCENE_MERGE_VIEW_NAMES))
    parser.add_argument("--analysis-merge-view-names", default=",".join(DEFAULT_ANALYSIS_MERGE_VIEW_NAMES))
    parser.add_argument("--refinement-merge-view-names", default=",".join(DEFAULT_REFINEMENT_MERGE_VIEW_NAMES))
    parser.add_argument("--scene-jpeg-quality", type=int, default=DEFAULT_SCENE_JPEG_QUALITY)
    parser.add_argument("--analysis-jpeg-quality", type=int, default=DEFAULT_ANALYSIS_JPEG_QUALITY)
    parser.add_argument("--refinement-jpeg-quality", type=int, default=DEFAULT_REFINEMENT_JPEG_QUALITY)
    parser.add_argument("--scene-min-api-frames", type=int, default=DEFAULT_SCENE_MIN_API_FRAMES)
    parser.add_argument("--analysis-min-api-frames", type=int, default=DEFAULT_ANALYSIS_MIN_API_FRAMES)
    parser.add_argument("--refinement-min-api-frames", type=int, default=DEFAULT_REFINEMENT_MIN_API_FRAMES)
    parser.add_argument("--scene-draw-timestamps", action=argparse.BooleanOptionalAction, default=DEFAULT_SCENE_DRAW_TIMESTAMPS)
    parser.add_argument("--analysis-draw-timestamps", action=argparse.BooleanOptionalAction, default=DEFAULT_ANALYSIS_DRAW_TIMESTAMPS)
    parser.add_argument("--refinement-draw-timestamps", action=argparse.BooleanOptionalAction, default=DEFAULT_REFINEMENT_DRAW_TIMESTAMPS)
    parser.add_argument("--scene-draw-viewposition", action=argparse.BooleanOptionalAction, default=DEFAULT_SCENE_DRAW_VIEWPOSITION)
    parser.add_argument("--analysis-draw-viewposition", action=argparse.BooleanOptionalAction, default=DEFAULT_ANALYSIS_DRAW_VIEWPOSITION)
    parser.add_argument("--refinement-draw-viewposition", action=argparse.BooleanOptionalAction, default=DEFAULT_REFINEMENT_DRAW_VIEWPOSITION)
    parser.add_argument("--max-frames", type=int, default=None, help="Compatibility override for all stage max frame settings.")
    parser.add_argument("--scene-merge-views", action=argparse.BooleanOptionalAction, default=DEFAULT_SCENE_MERGE_VIEWS)
    parser.add_argument("--analysis-merge-views", action=argparse.BooleanOptionalAction, default=DEFAULT_ANALYSIS_MERGE_VIEWS)
    parser.add_argument("--refinement-merge-views", action=argparse.BooleanOptionalAction, default=DEFAULT_REFINEMENT_MERGE_VIEWS)
    parser.add_argument("--scene-merge-mode", choices=["per_frame", "timeline_grid"], default=DEFAULT_SCENE_MERGE_MODE)
    parser.add_argument("--analysis-merge-mode", choices=["per_frame", "timeline_grid"], default=DEFAULT_ANALYSIS_MERGE_MODE)
    parser.add_argument("--refinement-merge-mode", choices=["per_frame", "timeline_grid"], default=DEFAULT_REFINEMENT_MERGE_MODE)
    parser.add_argument("--scene-merge-length", type=int, default=DEFAULT_SCENE_MERGE_LENGTH, help="Max time columns in timeline_grid mode; 0 means unlimited.")
    parser.add_argument("--analysis-merge-length", type=int, default=DEFAULT_ANALYSIS_MERGE_LENGTH, help="Max time columns in timeline_grid mode; 0 means unlimited.")
    parser.add_argument("--refinement-merge-length", type=int, default=DEFAULT_REFINEMENT_MERGE_LENGTH, help="Max time columns in timeline_grid mode; 0 means unlimited.")
    parser.add_argument("--merge-views", action=argparse.BooleanOptionalAction, default=None, help="Compatibility override for all stage merge switches.")
    parser.add_argument(
        "--save-processed-stages",
        default=",".join(DEFAULT_SAVE_PROCESSED_STAGES),
        help="Comma-separated stages to save processed media for: scene,analysis,refinement. Empty disables saving.",
    )
    parser.add_argument(
        "--save-processed-dir",
        default=DEFAULT_SAVE_PROCESSED_DIR,
        help="Root directory for saved processed media when --save-processed-stages is non-empty.",
    )
    parser.add_argument("--log-level", help="Override config logging.level for this CLI run.")
    parser.add_argument("--limit", type=int, help="Only process the first N records in batch mode.")
    parser.add_argument("--resume", action="store_true", help="Reuse successful items already in output JSON.")
    return parser.parse_args()


def assert_video_exists(path: Any) -> None:
    if isinstance(path, dict):
        for view_name, view_path in path.items():
            if not Path(str(view_path)).exists():
                raise FileNotFoundError(f"Video not found for view {view_name}: {view_path}")
        return
    if isinstance(path, list):
        for view_path in path:
            if not Path(str(view_path)).exists():
                raise FileNotFoundError(f"Video not found: {view_path}")
        return
    if not Path(str(path)).exists():
        raise FileNotFoundError(f"Video not found: {path}")


def parse_csv_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def run_one(
    client,
    *,
    main_video: Any,
    instruction: str,
    model: str = DEFAULT_MODEL,
    robot_type: str = DEFAULT_ROBOT_TYPE,
    prompt_language: str = DEFAULT_PROMPT_LANGUAGE,
    scene_fps: float = DEFAULT_SCENE_FPS,
    analysis_fps: float = DEFAULT_ANALYSIS_FPS,
    refinement_fps: float = DEFAULT_REFINEMENT_FPS,
    scene_input_mode: str = DEFAULT_SCENE_INPUT_MODE,
    analysis_input_mode: str = DEFAULT_ANALYSIS_INPUT_MODE,
    refinement_input_mode: str = DEFAULT_REFINEMENT_INPUT_MODE,
    scene_max_tokens: int = DEFAULT_SCENE_MAX_TOKENS,
    analysis_max_tokens: int = DEFAULT_ANALYSIS_MAX_TOKENS,
    refinement_max_tokens: int = DEFAULT_REFINEMENT_MAX_TOKENS,
    scene_resize_width: int = DEFAULT_SCENE_RESIZE_WIDTH,
    analysis_resize_width: int = DEFAULT_ANALYSIS_RESIZE_WIDTH,
    refinement_resize_width: int = DEFAULT_REFINEMENT_RESIZE_WIDTH,
    scene_max_frames: int = DEFAULT_SCENE_MAX_FRAMES,
    analysis_max_frames: int = DEFAULT_ANALYSIS_MAX_FRAMES,
    refinement_max_frames: int = DEFAULT_REFINEMENT_MAX_FRAMES,
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
    save_processed_stages: list[str] | None = None,
    save_processed_dir: str = DEFAULT_SAVE_PROCESSED_DIR,
) -> dict[str, Any]:
    assert_video_exists(main_video)
    result = run_vla_phase_annotation(
        client,
        video_path=main_video,
        initial_instruction=instruction,
        model=model,
        robot_type=robot_type,
        prompt_language=prompt_language,
        scene_fps=scene_fps,
        analysis_fps=analysis_fps,
        refinement_fps=refinement_fps,
        scene_input_mode=scene_input_mode,
        analysis_input_mode=analysis_input_mode,
        refinement_input_mode=refinement_input_mode,
        scene_max_tokens=scene_max_tokens,
        analysis_max_tokens=analysis_max_tokens,
        refinement_max_tokens=refinement_max_tokens,
        scene_resize_width=scene_resize_width,
        analysis_resize_width=analysis_resize_width,
        refinement_resize_width=refinement_resize_width,
        scene_max_frames=scene_max_frames,
        analysis_max_frames=analysis_max_frames,
        refinement_max_frames=refinement_max_frames,
        scene_merge_view_names=scene_merge_view_names,
        analysis_merge_view_names=analysis_merge_view_names,
        refinement_merge_view_names=refinement_merge_view_names,
        scene_jpeg_quality=scene_jpeg_quality,
        analysis_jpeg_quality=analysis_jpeg_quality,
        refinement_jpeg_quality=refinement_jpeg_quality,
        scene_min_api_frames=scene_min_api_frames,
        analysis_min_api_frames=analysis_min_api_frames,
        refinement_min_api_frames=refinement_min_api_frames,
        scene_draw_timestamps=scene_draw_timestamps,
        analysis_draw_timestamps=analysis_draw_timestamps,
        refinement_draw_timestamps=refinement_draw_timestamps,
        scene_draw_viewposition=scene_draw_viewposition,
        analysis_draw_viewposition=analysis_draw_viewposition,
        refinement_draw_viewposition=refinement_draw_viewposition,
        max_frames=max_frames,
        scene_merge_views=scene_merge_views,
        analysis_merge_views=analysis_merge_views,
        refinement_merge_views=refinement_merge_views,
        scene_merge_mode=scene_merge_mode,
        analysis_merge_mode=analysis_merge_mode,
        refinement_merge_mode=refinement_merge_mode,
        scene_merge_length=scene_merge_length,
        analysis_merge_length=analysis_merge_length,
        refinement_merge_length=refinement_merge_length,
        merge_views=merge_views,
        video_id=video_id,
        save_processed_stages=save_processed_stages,
        save_processed_dir=save_processed_dir,
    )
    return result.to_dict()


def load_records(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        data = data.get("items", data.get("data", data.get("records", [])))
    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list, or an object with items/data/records list.")
    return [dict(item) for item in data]


def record_key(record: dict[str, Any], index: int) -> str:
    return str(record.get("episode_id") or record.get("sample_id") or record.get("id") or index)


def load_existing_successes(path: str | None) -> dict[str, dict[str, Any]]:
    if not path or not Path(path).exists():
        return {}
    try:
        existing = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(existing, list):
        return {}
    successes = {}
    for i, item in enumerate(existing):
        key = record_key(item, i)
        prediction = item.get("prediction", {})
        if isinstance(prediction, dict) and prediction.get("success"):
            successes[key] = item
    return successes


def write_json(path: str, data: list[dict[str, Any]]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_batch(args: argparse.Namespace) -> None:
    if not args.output_json:
        raise ValueError("--output-json is required when --input-json is used.")

    records = load_records(args.input_json)
    if args.limit is not None:
        records = records[: args.limit]

    logger.info("Batch start records=%s input=%s output=%s resume=%s", len(records), args.input_json, args.output_json, args.resume)
    existing_successes = load_existing_successes(args.output_json) if args.resume else {}
    client = create_openai_client(api_key=args.api_key, base_url=args.base_url)
    outputs: list[dict[str, Any]] = []

    for index, record in enumerate(records):
        key = record_key(record, index)
        if key in existing_successes:
            outputs.append(existing_successes[key])
            print(f"[{index + 1}/{len(records)}] {key}: skipped existing success")
            continue

        main_video = record.get("video_path") or record.get("main_video_path") or record.get("main_video")
        instruction = record.get("task") or record.get("instruction") or record.get("initialInstruction")
        robot_type = record.get("robot_type") or args.robot_type
        prompt_language = record.get("prompt_language") or args.prompt_language

        merged = dict(record)
        start = time.time()
        try:
            if not main_video:
                raise ValueError("Missing video_path/main_video_path/main_video")
            if not instruction:
                raise ValueError("Missing task/instruction/initialInstruction")
            logger.info("[%s/%s] %s start", index + 1, len(records), key)
            prediction = run_one(
                client,
                main_video=main_video,
                instruction=str(instruction),
                model=args.model,
                robot_type=str(robot_type),
                prompt_language=str(prompt_language),
                scene_fps=args.scene_fps,
                analysis_fps=args.analysis_fps,
                refinement_fps=args.refinement_fps,
                scene_input_mode=args.scene_input_mode,
                analysis_input_mode=args.analysis_input_mode,
                refinement_input_mode=args.refinement_input_mode,
                scene_max_tokens=args.scene_max_tokens,
                analysis_max_tokens=args.analysis_max_tokens,
                refinement_max_tokens=args.refinement_max_tokens,
                scene_resize_width=args.scene_resize_width,
                analysis_resize_width=args.analysis_resize_width,
                refinement_resize_width=args.refinement_resize_width,
                scene_max_frames=args.scene_max_frames,
                analysis_max_frames=args.analysis_max_frames,
                refinement_max_frames=args.refinement_max_frames,
                scene_merge_view_names=parse_csv_list(args.scene_merge_view_names),
                analysis_merge_view_names=parse_csv_list(args.analysis_merge_view_names),
                refinement_merge_view_names=parse_csv_list(args.refinement_merge_view_names),
                scene_jpeg_quality=args.scene_jpeg_quality,
                analysis_jpeg_quality=args.analysis_jpeg_quality,
                refinement_jpeg_quality=args.refinement_jpeg_quality,
                scene_min_api_frames=args.scene_min_api_frames,
                analysis_min_api_frames=args.analysis_min_api_frames,
                refinement_min_api_frames=args.refinement_min_api_frames,
                scene_draw_timestamps=args.scene_draw_timestamps,
                analysis_draw_timestamps=args.analysis_draw_timestamps,
                refinement_draw_timestamps=args.refinement_draw_timestamps,
                scene_draw_viewposition=args.scene_draw_viewposition,
                analysis_draw_viewposition=args.analysis_draw_viewposition,
                refinement_draw_viewposition=args.refinement_draw_viewposition,
                max_frames=args.max_frames,
                scene_merge_views=args.scene_merge_views,
                analysis_merge_views=args.analysis_merge_views,
                refinement_merge_views=args.refinement_merge_views,
                scene_merge_mode=args.scene_merge_mode,
                analysis_merge_mode=args.analysis_merge_mode,
                refinement_merge_mode=args.refinement_merge_mode,
                scene_merge_length=args.scene_merge_length,
                analysis_merge_length=args.analysis_merge_length,
                refinement_merge_length=args.refinement_merge_length,
                merge_views=args.merge_views,
                video_id=key,
                save_processed_stages=parse_csv_list(args.save_processed_stages),
                save_processed_dir=args.save_processed_dir,
            )
            merged["prediction"] = prediction
            merged["error"] = None
            elapsed = time.time() - start
            logger.info("[%s/%s] %s success elapsed=%.2fs", index + 1, len(records), key, elapsed)
            print(f"[{index + 1}/{len(records)}] {key}: success")
        except Exception as exc:
            merged["prediction"] = None
            merged["error"] = str(exc)
            elapsed = time.time() - start
            logger.exception("[%s/%s] %s failed elapsed=%.2fs", index + 1, len(records), key, elapsed)
            print(f"[{index + 1}/{len(records)}] {key}: failed: {exc}")

        merged["processing_time_seconds"] = round(time.time() - start, 2)
        outputs.append(merged)
        write_json(args.output_json, outputs)

    write_json(args.output_json, outputs)
    logger.info("Batch done records=%s output=%s", len(outputs), args.output_json)
    print(f"Saved {len(outputs)} records to {args.output_json}")


def run_single(args: argparse.Namespace) -> None:
    if not args.main_video:
        raise ValueError("--main-video is required in single-video mode.")
    if not args.instruction:
        raise ValueError("--instruction is required in single-video mode.")

    client = create_openai_client(api_key=args.api_key, base_url=args.base_url)
    start = time.perf_counter()
    logger.info("Single run start video=%s", args.main_video)
    prediction = run_one(
        client,
        main_video=args.main_video,
        instruction=args.instruction,
        model=args.model,
        robot_type=args.robot_type,
        prompt_language=args.prompt_language,
        scene_fps=args.scene_fps,
        analysis_fps=args.analysis_fps,
        refinement_fps=args.refinement_fps,
        scene_input_mode=args.scene_input_mode,
        analysis_input_mode=args.analysis_input_mode,
        refinement_input_mode=args.refinement_input_mode,
        scene_max_tokens=args.scene_max_tokens,
        analysis_max_tokens=args.analysis_max_tokens,
        refinement_max_tokens=args.refinement_max_tokens,
        scene_resize_width=args.scene_resize_width,
        analysis_resize_width=args.analysis_resize_width,
        refinement_resize_width=args.refinement_resize_width,
        scene_max_frames=args.scene_max_frames,
        analysis_max_frames=args.analysis_max_frames,
        refinement_max_frames=args.refinement_max_frames,
        scene_merge_view_names=parse_csv_list(args.scene_merge_view_names),
        analysis_merge_view_names=parse_csv_list(args.analysis_merge_view_names),
        refinement_merge_view_names=parse_csv_list(args.refinement_merge_view_names),
        scene_jpeg_quality=args.scene_jpeg_quality,
        analysis_jpeg_quality=args.analysis_jpeg_quality,
        refinement_jpeg_quality=args.refinement_jpeg_quality,
        scene_min_api_frames=args.scene_min_api_frames,
        analysis_min_api_frames=args.analysis_min_api_frames,
        refinement_min_api_frames=args.refinement_min_api_frames,
        scene_draw_timestamps=args.scene_draw_timestamps,
        analysis_draw_timestamps=args.analysis_draw_timestamps,
        refinement_draw_timestamps=args.refinement_draw_timestamps,
        scene_draw_viewposition=args.scene_draw_viewposition,
        analysis_draw_viewposition=args.analysis_draw_viewposition,
        refinement_draw_viewposition=args.refinement_draw_viewposition,
        max_frames=args.max_frames,
        scene_merge_views=args.scene_merge_views,
        analysis_merge_views=args.analysis_merge_views,
        refinement_merge_views=args.refinement_merge_views,
        scene_merge_mode=args.scene_merge_mode,
        analysis_merge_mode=args.analysis_merge_mode,
        refinement_merge_mode=args.refinement_merge_mode,
        scene_merge_length=args.scene_merge_length,
        analysis_merge_length=args.analysis_merge_length,
        refinement_merge_length=args.refinement_merge_length,
        merge_views=args.merge_views,
        save_processed_stages=parse_csv_list(args.save_processed_stages),
        save_processed_dir=args.save_processed_dir,
    )
    logger.info("Single run done elapsed=%.2fs", time.perf_counter() - start)
    print(json.dumps(prediction, ensure_ascii=False, indent=2))


def main() -> None:
    args = parse_args()
    configure_logging(level=args.log_level) if args.log_level else configure_logging()
    if args.main_video:
        run_single(args)
    else:
        run_batch(args)


if __name__ == "__main__":
    main()
