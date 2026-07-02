r"""Run no-steps-raw VLM annotation on one video or a JSON batch.

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
DEFAULT_OUTPUT_JSON = EXAMPLE_DIR / "robot_mind2_camera_top_predictions.json"

from vlm_auto_annotation import create_openai_client
from vlm_auto_annotation.flows import (
    run_multiview_no_steps_raw,
    run_single_view_no_steps_raw,
)
from vlm_auto_annotation.utils.config import (
    DEFAULT_ANALYSIS_FPS,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_FRAMES,
    DEFAULT_MODEL,
    DEFAULT_REFINEMENT_FPS,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run no-steps-raw VLM annotation.")
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
    parser.add_argument("--detail-video", help="Optional path to the wrist/detail/auxiliary view video.")
    parser.add_argument("--detail-view-name", default="wrist", help="Name of the detail view.")
    parser.add_argument(
        "--instruction",
        help="Initial task instruction, for example: 'pick up the cup and place it on the plate'.",
    )
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "EMPTY"))
    parser.add_argument("--base-url", default=os.environ.get("ANNOTATE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--model", default=os.environ.get("ANNOTATE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--analysis-fps", type=float, default=DEFAULT_ANALYSIS_FPS)
    parser.add_argument("--refinement-fps", type=float, default=DEFAULT_REFINEMENT_FPS)
    parser.add_argument("--max-frames", type=int, default=DEFAULT_MAX_FRAMES)
    parser.add_argument("--limit", type=int, help="Only process the first N records in batch mode.")
    parser.add_argument("--resume", action="store_true", help="Reuse successful items already in output JSON.")
    return parser.parse_args()


def assert_video_exists(path: str) -> None:
    if not Path(path).exists():
        raise FileNotFoundError(f"Video not found: {path}")


def run_one(
    client,
    *,
    main_video: str,
    instruction: str,
    detail_video: str | None = None,
    detail_view_name: str = "wrist",
    model: str = DEFAULT_MODEL,
    analysis_fps: float = DEFAULT_ANALYSIS_FPS,
    refinement_fps: float = DEFAULT_REFINEMENT_FPS,
    max_frames: int = DEFAULT_MAX_FRAMES,
) -> dict[str, Any]:
    assert_video_exists(main_video)
    if detail_video:
        assert_video_exists(detail_video)
        result = run_multiview_no_steps_raw(
            client,
            main_video_path=main_video,
            detail_video_path=detail_video,
            detail_view_name=detail_view_name,
            initial_instruction=instruction,
            model=model,
            analysis_fps=analysis_fps,
            refinement_fps=refinement_fps,
            max_frames=max_frames,
        )
    else:
        result = run_single_view_no_steps_raw(
            client,
            video_path=main_video,
            initial_instruction=instruction,
            model=model,
            analysis_fps=analysis_fps,
            refinement_fps=refinement_fps,
            max_frames=max_frames,
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
        detail_video = record.get("detail_video_path") or record.get("detail_video")
        instruction = record.get("task") or record.get("instruction") or record.get("initialInstruction")

        merged = dict(record)
        start = time.time()
        try:
            if not main_video:
                raise ValueError("Missing video_path/main_video_path/main_video")
            if not instruction:
                raise ValueError("Missing task/instruction/initialInstruction")
            prediction = run_one(
                client,
                main_video=str(main_video),
                detail_video=str(detail_video) if detail_video else None,
                detail_view_name=args.detail_view_name,
                instruction=str(instruction),
                model=args.model,
                analysis_fps=args.analysis_fps,
                refinement_fps=args.refinement_fps,
                max_frames=args.max_frames,
            )
            merged["prediction"] = prediction
            merged["error"] = None
            print(f"[{index + 1}/{len(records)}] {key}: success")
        except Exception as exc:
            merged["prediction"] = None
            merged["error"] = str(exc)
            print(f"[{index + 1}/{len(records)}] {key}: failed: {exc}")

        merged["processing_time_seconds"] = round(time.time() - start, 2)
        outputs.append(merged)
        write_json(args.output_json, outputs)

    write_json(args.output_json, outputs)
    print(f"Saved {len(outputs)} records to {args.output_json}")


def run_single(args: argparse.Namespace) -> None:
    if not args.main_video:
        raise ValueError("--main-video is required in single-video mode.")
    if not args.instruction:
        raise ValueError("--instruction is required in single-video mode.")

    client = create_openai_client(api_key=args.api_key, base_url=args.base_url)
    prediction = run_one(
        client,
        main_video=args.main_video,
        detail_video=args.detail_video,
        detail_view_name=args.detail_view_name,
        instruction=args.instruction,
        model=args.model,
        analysis_fps=args.analysis_fps,
        refinement_fps=args.refinement_fps,
        max_frames=args.max_frames,
    )
    print(json.dumps(prediction, ensure_ascii=False, indent=2))


def main() -> None:
    args = parse_args()
    if args.main_video:
        run_single(args)
    else:
        run_batch(args)


if __name__ == "__main__":
    main()
