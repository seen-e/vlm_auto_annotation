"""Video frame sampling utilities for VLM requests."""

from __future__ import annotations

import base64
import io
import json
import logging
from pathlib import Path
import time
from typing import Any

try:
    from .config import (
        DEFAULT_ANALYSIS_DRAW_TIMESTAMPS,
        DEFAULT_ANALYSIS_FPS,
        DEFAULT_DRAW_TIMESTAMPS,
        DEFAULT_JPEG_QUALITY,
        DEFAULT_MAX_FRAMES,
        DEFAULT_MERGE_VIEW_NAMES,
        DEFAULT_ANALYSIS_RESIZE_WIDTH,
        DEFAULT_REFINEMENT_FPS,
        DEFAULT_REFINEMENT_DRAW_TIMESTAMPS,
        DEFAULT_REFINEMENT_RESIZE_WIDTH,
        DEFAULT_RESIZE_WIDTH,
        MIN_API_FRAMES,
    )
    from .logging_utils import configure_logging
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from utils.config import (
        DEFAULT_ANALYSIS_DRAW_TIMESTAMPS,
        DEFAULT_ANALYSIS_FPS,
        DEFAULT_DRAW_TIMESTAMPS,
        DEFAULT_JPEG_QUALITY,
        DEFAULT_MAX_FRAMES,
        DEFAULT_MERGE_VIEW_NAMES,
        DEFAULT_ANALYSIS_RESIZE_WIDTH,
        DEFAULT_REFINEMENT_FPS,
        DEFAULT_REFINEMENT_DRAW_TIMESTAMPS,
        DEFAULT_REFINEMENT_RESIZE_WIDTH,
        DEFAULT_RESIZE_WIDTH,
        MIN_API_FRAMES,
    )
    from utils.logging_utils import configure_logging


logger = logging.getLogger(__name__)


def _sample_indices(total_frames: int, fps: float, target_fps: float, max_frames: int) -> list[int]:
    if total_frames <= 0:
        return []
    if fps <= 0 or target_fps <= 0:
        indices = list(range(total_frames))
    else:
        interval = max(1, int(round(fps / target_fps)))
        indices = list(range(0, total_frames, interval))
    if len(indices) > max_frames:
        step = (total_frames - 1) / max(max_frames - 1, 1)
        indices = [int(round(i * step)) for i in range(max_frames)]
    return sorted(set(i for i in indices if 0 <= i < total_frames))


def _encode_jpeg(frame, resize_width: int, jpeg_quality: int) -> str:
    try:
        import cv2

        h, w = frame.shape[:2]
        if resize_width and w > resize_width:
            new_h = int(round(h * resize_width / w))
            frame = cv2.resize(frame, (resize_width, new_h), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
        if not ok:
            raise RuntimeError("cv2.imencode failed")
        return base64.b64encode(buf.tobytes()).decode("utf-8")
    except ImportError:
        from PIL import Image

        img = Image.fromarray(frame[:, :, ::-1])
        if resize_width and img.width > resize_width:
            new_h = int(round(img.height * resize_width / img.width))
            img = img.resize((resize_width, new_h))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=jpeg_quality)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _resize_frame(frame, resize_width: int):
    import cv2

    h, w = frame.shape[:2]
    if resize_width and w > resize_width:
        new_h = int(round(h * resize_width / w))
        return cv2.resize(frame, (resize_width, new_h), interpolation=cv2.INTER_AREA)
    return frame


def _pad_to_size(frame, width: int, height: int):
    import cv2

    h, w = frame.shape[:2]
    if h == height and w == width:
        return frame
    bottom = max(0, height - h)
    right = max(0, width - w)
    return cv2.copyMakeBorder(frame, 0, bottom, 0, right, cv2.BORDER_CONSTANT, value=(0, 0, 0))


def _stack_view_frames(frames: list[Any]) -> Any:
    import cv2

    if not frames:
        raise ValueError("No frames to stack")
    max_w = max(frame.shape[1] for frame in frames)
    max_h = max(frame.shape[0] for frame in frames)
    padded = [_pad_to_size(frame, max_w, max_h) for frame in frames]
    return cv2.vconcat(padded)


def _encode_jpeg_preprocessed(frame, jpeg_quality: int) -> str:
    import cv2

    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _format_timestamp(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    return f"{minutes:02d}:{secs:05.2f}"


def _draw_timestamp(frame, timestamp: str):
    import cv2

    text = f"t={timestamp}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.6
    thickness = 2
    margin = 8
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    x1, y1 = margin, margin
    x2 = x1 + tw + margin
    y2 = y1 + th + baseline + margin
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), -1)
    cv2.putText(frame, text, (x1 + margin // 2, y2 - baseline - margin // 2), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return frame


def _select_video_views(
    video_path: str | Path | list[str | Path] | dict[str, str | Path],
    view_names: list[str] | None,
) -> list[tuple[str, str]]:
    if isinstance(video_path, dict):
        available = [(str(name), str(path)) for name, path in video_path.items()]
        if view_names:
            by_name = dict(available)
            missing = [name for name in view_names if name not in by_name]
            if missing:
                raise KeyError(f"Requested view(s) not found: {missing}. Available views: {list(by_name)}")
            return [(name, by_name[name]) for name in view_names]
        return available[:1]
    if isinstance(video_path, (list, tuple)):
        available = [(Path(path).parent.name, str(path)) for path in video_path]
        if view_names:
            by_name = dict(available)
            missing = [name for name in view_names if name not in by_name]
            if missing:
                raise KeyError(f"Requested view(s) not found: {missing}. Available views: {list(by_name)}")
            return [(name, by_name[name]) for name in view_names]
        return available[:1]
    return [(Path(video_path).parent.name, str(video_path))]


def load_video_as_image_parts(
    video_path: str | Path,
    *,
    target_fps: float,
    max_frames: int = DEFAULT_MAX_FRAMES,
    frame_start: int = 0,
    frame_end: int | None = None,
    resize_width: int = DEFAULT_RESIZE_WIDTH,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
    draw_timestamps: bool = DEFAULT_DRAW_TIMESTAMPS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load sampled video frames as OpenAI image_url parts."""
    import cv2

    start_time = time.perf_counter()
    path = str(video_path)
    logger.info(
        "Load video frames start path=%s target_fps=%s max_frames=%s resize_width=%s draw_timestamps=%s",
        path,
        target_fps,
        max_frames,
        resize_width,
        draw_timestamps,
    )
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {path}")

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        start = max(0, int(frame_start or 0))
        end = min(total_frames, int(frame_end) + 1) if frame_end is not None else total_frames
        span = max(0, end - start)
        local_indices = _sample_indices(span, fps, target_fps, max_frames)
        indices = [start + i for i in local_indices]
        if 0 < len(indices) < MIN_API_FRAMES and span >= MIN_API_FRAMES:
            step = (span - 1) / max(MIN_API_FRAMES - 1, 1)
            indices = sorted(set(start + int(round(i * step)) for i in range(MIN_API_FRAMES)))

        parts: list[dict[str, Any]] = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                continue
            frame = _resize_frame(frame, resize_width)
            if draw_timestamps:
                frame = _draw_timestamp(frame, _format_timestamp(idx / max(fps, 1e-6)))
            b64 = _encode_jpeg_preprocessed(frame, jpeg_quality)
            parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

        if not parts:
            raise RuntimeError(f"No frames sampled from {path}")

        elapsed = time.perf_counter() - start_time
        logger.info(
            "Load video frames done path=%s elapsed=%.2fs sampled_frames=%s total_frames=%s fps=%s",
            path,
            elapsed,
            len(parts),
            total_frames,
            fps,
        )
        return parts, {
            "video_path": path,
            "video_fps": fps,
            "total_frames": total_frames,
            "sampled_frames": len(parts),
            "frame_range": [start, end],
            "draw_timestamps": draw_timestamps,
            "load_elapsed_seconds": round(elapsed, 3),
        }
    finally:
        cap.release()


def load_video_or_views_as_image_parts(
    video_path: str | Path | list[str | Path] | dict[str, str | Path],
    *,
    target_fps: float,
    max_frames: int = DEFAULT_MAX_FRAMES,
    frame_start: int = 0,
    frame_end: int | None = None,
    resize_width: int = DEFAULT_RESIZE_WIDTH,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
    draw_timestamps: bool = DEFAULT_DRAW_TIMESTAMPS,
    view_names: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load one video or time-aligned multi-view videos as image_url parts."""
    start_time = time.perf_counter()
    selected = _select_video_views(video_path, view_names or DEFAULT_MERGE_VIEW_NAMES)
    if len(selected) == 1:
        parts, meta = load_video_as_image_parts(
            selected[0][1],
            target_fps=target_fps,
            max_frames=max_frames,
            frame_start=frame_start,
            frame_end=frame_end,
            resize_width=resize_width,
            jpeg_quality=jpeg_quality,
            draw_timestamps=draw_timestamps,
        )
        meta["selected_views"] = [selected[0][0]]
        meta["input_mode"] = "single_view"
        return parts, meta

    import cv2

    logger.info(
        "Load merged views start views=%s target_fps=%s max_frames=%s resize_width=%s draw_timestamps=%s",
        [name for name, _ in selected],
        target_fps,
        max_frames,
        resize_width,
        draw_timestamps,
    )
    caps = []
    try:
        for view_name, path in selected:
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                raise FileNotFoundError(f"Could not open video for view {view_name}: {path}")
            caps.append((view_name, path, cap))

        total_frames_by_view = {name: int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) for name, _, cap in caps}
        fps_by_view = {name: float(cap.get(cv2.CAP_PROP_FPS) or 30.0) for name, _, cap in caps}
        total_frames = min(total_frames_by_view.values()) if total_frames_by_view else 0
        fps = min(fps_by_view.values()) if fps_by_view else 30.0
        start = max(0, int(frame_start or 0))
        end = min(total_frames, int(frame_end) + 1) if frame_end is not None else total_frames
        span = max(0, end - start)
        local_indices = _sample_indices(span, fps, target_fps, max_frames)
        indices = [start + i for i in local_indices]
        if 0 < len(indices) < MIN_API_FRAMES and span >= MIN_API_FRAMES:
            step = (span - 1) / max(MIN_API_FRAMES - 1, 1)
            indices = sorted(set(start + int(round(i * step)) for i in range(MIN_API_FRAMES)))

        parts: list[dict[str, Any]] = []
        for idx in indices:
            frames = []
            for _, _, cap in caps:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if not ok:
                    frames = []
                    break
                frames.append(_resize_frame(frame, resize_width))
            if not frames:
                continue
            merged = _stack_view_frames(frames)
            if draw_timestamps:
                merged = _draw_timestamp(merged, _format_timestamp(idx / max(fps, 1e-6)))
            b64 = _encode_jpeg_preprocessed(merged, jpeg_quality)
            parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

        if not parts:
            raise RuntimeError(f"No frames sampled from selected views: {[path for _, path in selected]}")

        elapsed = time.perf_counter() - start_time
        logger.info(
            "Load merged views done elapsed=%.2fs sampled_frames=%s selected_views=%s total_frames=%s fps=%s",
            elapsed,
            len(parts),
            [name for name, _, _ in caps],
            total_frames,
            fps,
        )
        return parts, {
            "video_path": {name: path for name, path, _ in caps},
            "selected_views": [name for name, _, _ in caps],
            "input_mode": "merged_views",
            "merge_layout": "vertical",
            "video_fps": fps,
            "video_fps_by_view": fps_by_view,
            "total_frames": total_frames,
            "total_frames_by_view": total_frames_by_view,
            "sampled_frames": len(parts),
            "frame_range": [start, end],
            "draw_timestamps": draw_timestamps,
            "load_elapsed_seconds": round(elapsed, 3),
        }
    finally:
        for _, _, cap in caps:
            cap.release()


def labelled_view_parts(view_name: str, parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefix image parts with a text label naming the view."""
    return [{"type": "text", "text": f"[View: {view_name}]"}, *parts]


def _parse_cli_bool(value: str) -> bool:
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Expected a boolean value, got: {value}")


def _strip_data_url(value: str) -> str:
    prefix = "data:image/jpeg;base64,"
    return value[len(prefix) :] if value.startswith(prefix) else value


def _load_debug_video_path(args) -> str | list[str] | dict[str, str]:
    if args.tasks_json:
        with Path(args.tasks_json).open("r", encoding="utf-8") as f:
            tasks = json.load(f)
        task = tasks[int(args.task_index)]
        return task["video_path"]
    if args.video_json:
        with Path(args.video_json).open("r", encoding="utf-8") as f:
            return json.load(f)
    if args.video:
        return args.video
    if args.videos:
        return args.videos

    raise ValueError("Provide --video, --videos, --video-json, or --tasks-json.")


def _save_debug_parts(parts: list[dict[str, Any]], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for index, part in enumerate(parts):
        url = part.get("image_url", {}).get("url", "")
        if not url:
            continue
        path = output_dir / f"frame_{index:04d}.jpg"
        path.write_bytes(base64.b64decode(_strip_data_url(url)))
        saved.append(str(path))
    return saved


def _main() -> None:
    import argparse

    default_tasks_json = Path(__file__).resolve().parents[1] / "example" / "robot_mind2_camera_top_tasks.json"
    parser = argparse.ArgumentParser(description="Sample video frames, merge configured views, draw timestamps, and save JPEGs.")
    parser.add_argument("--video", help="Path to one MP4/video file.")
    parser.add_argument("--videos", nargs="+", help="Paths to multiple MP4/video files. View names use each parent folder name.")
    parser.add_argument("--video-json", help="JSON file containing a video_path dict/list/string.")
    parser.add_argument(
        "--tasks-json",
        default=str(default_tasks_json) if default_tasks_json.exists() else None,
        help="Task JSON file. The selected task's video_path will be used.",
    )
    parser.add_argument("--task-index", type=int, default=0, help="Task index for --tasks-json.")
    parser.add_argument("--output-dir", default="debug_frames/multiview_timestamp_default", help="Directory for saved JPEG frames.")
    parser.add_argument("--target-fps", type=float, help="Sampling FPS. Defaults to the selected stage FPS.")
    parser.add_argument("--max-frames", type=int, default=DEFAULT_MAX_FRAMES, help="Maximum sampled frames.")
    parser.add_argument("--log-level", help="Override config logging.level for this debug run.")
    parser.add_argument("--frame-start", type=int, default=0, help="Inclusive start frame index.")
    parser.add_argument("--frame-end", type=int, default=None, help="Inclusive end frame index.")
    parser.add_argument(
        "--stage",
        choices=["analysis", "refinement"],
        default="refinement",
        help="Stage defaults to use when --resize-width is not provided.",
    )
    parser.add_argument("--resize-width", type=int, help="Per-view resize width before merge.")
    parser.add_argument("--analysis-resize-width", type=int, default=DEFAULT_ANALYSIS_RESIZE_WIDTH)
    parser.add_argument("--refinement-resize-width", type=int, default=DEFAULT_REFINEMENT_RESIZE_WIDTH)
    parser.add_argument("--jpeg-quality", type=int, default=DEFAULT_JPEG_QUALITY, help="JPEG quality.")
    parser.add_argument(
        "--view-names",
        default=",".join(DEFAULT_MERGE_VIEW_NAMES),
        help="Comma-separated view names to select. Empty string means first input view.",
    )
    parser.add_argument(
        "--draw-timestamps",
        type=_parse_cli_bool,
        default=None,
        help="Whether to draw black-background white timestamps.",
    )
    args = parser.parse_args()
    configure_logging(level=args.log_level) if args.log_level else configure_logging()

    view_names = [item.strip() for item in args.view_names.split(",") if item.strip()]
    video_path = _load_debug_video_path(args)
    resize_width = args.resize_width
    if resize_width is None:
        resize_width = args.analysis_resize_width if args.stage == "analysis" else args.refinement_resize_width
    target_fps = args.target_fps
    if target_fps is None:
        target_fps = DEFAULT_ANALYSIS_FPS if args.stage == "analysis" else DEFAULT_REFINEMENT_FPS
    draw_timestamps = args.draw_timestamps
    if draw_timestamps is None:
        draw_timestamps = (
            DEFAULT_ANALYSIS_DRAW_TIMESTAMPS if args.stage == "analysis" else DEFAULT_REFINEMENT_DRAW_TIMESTAMPS
        )
    parts, meta = load_video_or_views_as_image_parts(
        video_path,
        target_fps=target_fps,
        max_frames=args.max_frames,
        frame_start=args.frame_start,
        frame_end=args.frame_end,
        resize_width=resize_width,
        jpeg_quality=args.jpeg_quality,
        draw_timestamps=draw_timestamps,
        view_names=view_names,
    )

    output_dir = Path(args.output_dir)
    saved = _save_debug_parts(parts, output_dir)
    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved debug frames count=%s output_dir=%s metadata=%s", len(saved), output_dir, meta_path)
    print(json.dumps({"saved_frames": saved, "metadata": str(meta_path), **meta}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
