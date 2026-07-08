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
        DEFAULT_ANALYSIS_JPEG_QUALITY,
        DEFAULT_ANALYSIS_MAX_FRAMES,
        DEFAULT_ANALYSIS_MERGE_VIEW_NAMES,
        DEFAULT_DRAW_TIMESTAMPS,
        DEFAULT_JPEG_QUALITY,
        DEFAULT_MERGE_MODE,
        DEFAULT_MAX_FRAMES,
        DEFAULT_MERGE_VIEWS,
        DEFAULT_MERGE_VIEW_NAMES,
        DEFAULT_ANALYSIS_MERGE_MODE,
        DEFAULT_ANALYSIS_MERGE_VIEWS,
        DEFAULT_REFINEMENT_MERGE_MODE,
        DEFAULT_REFINEMENT_MERGE_VIEWS,
        DEFAULT_SCENE_MERGE_MODE,
        DEFAULT_SCENE_MERGE_VIEWS,
        DEFAULT_SCENE_DRAW_TIMESTAMPS,
        DEFAULT_SCENE_FPS,
        DEFAULT_SCENE_RESIZE_WIDTH,
        DEFAULT_ANALYSIS_RESIZE_WIDTH,
        DEFAULT_REFINEMENT_FPS,
        DEFAULT_REFINEMENT_DRAW_TIMESTAMPS,
        DEFAULT_SCENE_DRAW_VIEWPOSITION,
        DEFAULT_ANALYSIS_DRAW_VIEWPOSITION,
        DEFAULT_REFINEMENT_DRAW_VIEWPOSITION,
        DEFAULT_REFINEMENT_JPEG_QUALITY,
        DEFAULT_REFINEMENT_MAX_FRAMES,
        DEFAULT_REFINEMENT_MERGE_VIEW_NAMES,
        DEFAULT_REFINEMENT_RESIZE_WIDTH,
        DEFAULT_RESIZE_WIDTH,
        DEFAULT_SCENE_JPEG_QUALITY,
        DEFAULT_SCENE_MAX_FRAMES,
        DEFAULT_SCENE_MERGE_VIEW_NAMES,
        MIN_API_FRAMES,
        DEFAULT_SCENE_MIN_API_FRAMES,
        DEFAULT_ANALYSIS_MIN_API_FRAMES,
        DEFAULT_REFINEMENT_MIN_API_FRAMES,
        DEFAULT_SCENE_MERGE_LENGTH,
        DEFAULT_ANALYSIS_MERGE_LENGTH,
        DEFAULT_REFINEMENT_MERGE_LENGTH,
    )
    from .logging_utils import configure_logging
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from utils.config import (
        DEFAULT_ANALYSIS_DRAW_TIMESTAMPS,
        DEFAULT_ANALYSIS_FPS,
        DEFAULT_ANALYSIS_JPEG_QUALITY,
        DEFAULT_ANALYSIS_MAX_FRAMES,
        DEFAULT_ANALYSIS_MERGE_VIEW_NAMES,
        DEFAULT_DRAW_TIMESTAMPS,
        DEFAULT_JPEG_QUALITY,
        DEFAULT_MERGE_MODE,
        DEFAULT_MAX_FRAMES,
        DEFAULT_MERGE_VIEWS,
        DEFAULT_MERGE_VIEW_NAMES,
        DEFAULT_ANALYSIS_MERGE_MODE,
        DEFAULT_ANALYSIS_MERGE_VIEWS,
        DEFAULT_REFINEMENT_MERGE_MODE,
        DEFAULT_REFINEMENT_MERGE_VIEWS,
        DEFAULT_SCENE_MERGE_MODE,
        DEFAULT_SCENE_MERGE_VIEWS,
        DEFAULT_SCENE_DRAW_TIMESTAMPS,
        DEFAULT_SCENE_FPS,
        DEFAULT_SCENE_RESIZE_WIDTH,
        DEFAULT_ANALYSIS_RESIZE_WIDTH,
        DEFAULT_REFINEMENT_FPS,
        DEFAULT_REFINEMENT_DRAW_TIMESTAMPS,
        DEFAULT_SCENE_DRAW_VIEWPOSITION,
        DEFAULT_ANALYSIS_DRAW_VIEWPOSITION,
        DEFAULT_REFINEMENT_DRAW_VIEWPOSITION,
        DEFAULT_REFINEMENT_JPEG_QUALITY,
        DEFAULT_REFINEMENT_MAX_FRAMES,
        DEFAULT_REFINEMENT_MERGE_VIEW_NAMES,
        DEFAULT_REFINEMENT_RESIZE_WIDTH,
        DEFAULT_RESIZE_WIDTH,
        DEFAULT_SCENE_JPEG_QUALITY,
        DEFAULT_SCENE_MAX_FRAMES,
        DEFAULT_SCENE_MERGE_VIEW_NAMES,
        MIN_API_FRAMES,
        DEFAULT_SCENE_MIN_API_FRAMES,
        DEFAULT_ANALYSIS_MIN_API_FRAMES,
        DEFAULT_REFINEMENT_MIN_API_FRAMES,
        DEFAULT_SCENE_MERGE_LENGTH,
        DEFAULT_ANALYSIS_MERGE_LENGTH,
        DEFAULT_REFINEMENT_MERGE_LENGTH,
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


def _draw_timestamp(frame, timestamp: str | None, view_label: str | None = None):
    """Draw black-background white timestamp and optional view label at top-left."""
    import cv2

    parts: list[str] = []
    if timestamp:
        parts.append(f"t={timestamp}")
    if view_label:
        parts.append(str(view_label))
    if not parts:
        return frame
    text = "  |  ".join(parts)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thickness = 1
    margin = 5
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    x1, y1 = margin, margin
    x2 = x1 + tw + margin
    y2 = y1 + th + baseline + margin
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), -1)
    cv2.putText(frame, text, (x1 + margin // 2, y2 - baseline - margin // 2), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return frame


def _draw_view_label(frame, view_name: str | None):
    """DEPRECATED: kept for other callers, delegates to _draw_timestamp."""
    return _draw_timestamp(frame, None, view_name)


def _draw_label(frame, text: str, origin: tuple[int, int], *, scale: float = 0.55, thickness: int = 1):
    import cv2

    x, y = origin
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, str(text), (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return frame


def _normalize_merge_mode(value: str | None) -> str:
    mode = str(value or DEFAULT_MERGE_MODE).strip().lower().replace("-", "_")
    aliases = {
        "frame": "per_frame",
        "frames": "per_frame",
        "vertical": "per_frame",
        "grid": "timeline_grid",
        "timeline": "timeline_grid",
        "time_grid": "timeline_grid",
    }
    mode = aliases.get(mode, mode)
    if mode not in {"per_frame", "timeline_grid"}:
        raise ValueError(f"merge_mode must be 'per_frame' or 'timeline_grid', got: {value}")
    return mode


def _select_video_views(
    video_path: str | Path | list[str | Path] | dict[str, str | Path],
    view_names: list[str] | None,
    *,
    merge_views: bool = True,
) -> list[tuple[str, str]]:
    if isinstance(video_path, dict):
        available = [(str(name), str(path)) for name, path in video_path.items()]
        if not merge_views:
            return available[:1]
        if view_names:
            by_name = dict(available)
            missing = [name for name in view_names if name not in by_name]
            if missing:
                raise KeyError(f"Requested view(s) not found: {missing}. Available views: {list(by_name)}")
            return [(name, by_name[name]) for name in view_names]
        return available[:1]
    if isinstance(video_path, (list, tuple)):
        available = [(Path(path).parent.name, str(path)) for path in video_path]
        if not merge_views:
            return available[:1]
        if view_names:
            by_name = dict(available)
            missing = [name for name in view_names if name not in by_name]
            if missing:
                raise KeyError(f"Requested view(s) not found: {missing}. Available views: {list(by_name)}")
            return [(name, by_name[name]) for name in view_names]
        return available[:1]
    return [(Path(video_path).parent.name, str(video_path))]


def _build_timeline_grid(
    *,
    cells_by_time: list[list[Any]],
    view_names: list[str],
    timestamps: list[str],
) -> Any:
    import cv2
    import numpy as np

    if not cells_by_time:
        raise ValueError("No frames to build timeline grid")

    flat_cells = [frame for frames in cells_by_time for frame in frames]
    cell_w = max(frame.shape[1] for frame in flat_cells)
    cell_h = max(frame.shape[0] for frame in flat_cells)
    left_header_w = max(180, min(360, 12 * max((len(name) for name in view_names), default=8)))
    top_header_h = 36

    rows = len(view_names)
    cols = len(cells_by_time)
    canvas_h = top_header_h + rows * cell_h
    canvas_w = left_header_w + cols * cell_w
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

    for col, timestamp in enumerate(timestamps):
        x = left_header_w + col * cell_w
        _draw_label(canvas, f"t={timestamp}", (x + 8, 24), scale=0.55, thickness=1)
        cv2.line(canvas, (x, 0), (x, canvas_h), (70, 70, 70), 1)

    for row, view_name in enumerate(view_names):
        y = top_header_h + row * cell_h
        _draw_label(canvas, view_name, (8, y + 24), scale=0.5, thickness=1)
        cv2.line(canvas, (0, y), (canvas_w, y), (70, 70, 70), 1)

    cv2.line(canvas, (left_header_w, 0), (left_header_w, canvas_h), (110, 110, 110), 2)
    cv2.line(canvas, (0, top_header_h), (canvas_w, top_header_h), (110, 110, 110), 2)

    for col, frames in enumerate(cells_by_time):
        for row, frame in enumerate(frames):
            cell = _pad_to_size(frame, cell_w, cell_h)
            y = top_header_h + row * cell_h
            x = left_header_w + col * cell_w
            canvas[y : y + cell_h, x : x + cell_w] = cell

    return canvas


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
    draw_viewposition: bool = False,
    view_label: str | None = None,
    min_api_frames: int = MIN_API_FRAMES,
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
        if 0 < len(indices) < min_api_frames and span >= min_api_frames:
            step = (span - 1) / max(min_api_frames - 1, 1)
            indices = sorted(set(start + int(round(i * step)) for i in range(min_api_frames)))

        parts: list[dict[str, Any]] = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                continue
            frame = _resize_frame(frame, resize_width)
            if draw_timestamps or draw_viewposition:
                ts = _format_timestamp(idx / max(fps, 1e-6)) if draw_timestamps else None
                vl = view_label if draw_viewposition else None
                frame = _draw_timestamp(frame, ts, vl)
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
            "max_frames": max_frames,
            "frame_range": [start, end],
            "jpeg_quality": jpeg_quality,
            "draw_timestamps": draw_timestamps,
            "draw_viewposition": draw_viewposition,
            "min_api_frames": min_api_frames,
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
    draw_viewposition: bool = False,
    min_api_frames: int = MIN_API_FRAMES,
    merge_length: int = 0,
    view_names: list[str] | None = None,
    merge_views: bool = DEFAULT_MERGE_VIEWS,
    merge_mode: str = DEFAULT_MERGE_MODE,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load one video or time-aligned multi-view videos as image_url parts."""
    start_time = time.perf_counter()
    merge_mode = _normalize_merge_mode(merge_mode)
    selected = _select_video_views(video_path, view_names or DEFAULT_MERGE_VIEW_NAMES, merge_views=merge_views)
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
            draw_viewposition=draw_viewposition,
            view_label=selected[0][0] if draw_viewposition else None,
            min_api_frames=min_api_frames,
        )
        meta["selected_views"] = [selected[0][0]]
        meta["input_mode"] = "single_view"
        meta["merge_views"] = merge_views
        meta["merge_mode"] = "single_view"
        meta["image_parts"] = len(parts)
        return parts, meta

    import cv2

    logger.info(
        "Load merged views start views=%s target_fps=%s max_frames=%s resize_width=%s draw_timestamps=%s merge_mode=%s",
        [name for name, _ in selected],
        target_fps,
        max_frames,
        resize_width,
        draw_timestamps,
        merge_mode,
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
        if 0 < len(indices) < min_api_frames and span >= min_api_frames:
            step = (span - 1) / max(min_api_frames - 1, 1)
            indices = sorted(set(start + int(round(i * step)) for i in range(min_api_frames)))

        parts: list[dict[str, Any]] = []
        if merge_mode == "timeline_grid":
            # Apply merge_length: chunk indices into groups, one grid image per group
            if merge_length > 0:
                index_chunks = [indices[i : i + merge_length] for i in range(0, len(indices), merge_length)]
            else:
                index_chunks = [indices]

            view_names = [name for name, _, _ in caps]
            for chunk in index_chunks:
                cells_by_time: list[list[Any]] = []
                timestamps: list[str] = []
                for idx in chunk:
                    frames = []
                    for view_name, _, cap in caps:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                        ok, frame = cap.read()
                        if not ok:
                            frames = []
                            break
                        frame = _resize_frame(frame, resize_width)
                        if draw_timestamps or draw_viewposition:
                            ts = _format_timestamp(idx / max(fps, 1e-6)) if draw_timestamps else None
                            vl = view_name if draw_viewposition else None
                            frame = _draw_timestamp(frame, ts, vl)
                        frames.append(frame)
                    if frames:
                        cells_by_time.append(frames)
                        timestamps.append(_format_timestamp(idx / max(fps, 1e-6)))

                if not cells_by_time:
                    continue
                grid = _build_timeline_grid(
                    cells_by_time=cells_by_time,
                    view_names=view_names,
                    timestamps=timestamps,
                )
                b64 = _encode_jpeg_preprocessed(grid, jpeg_quality)
                parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

            if not parts:
                raise RuntimeError(f"No frames sampled from selected views: {[path for _, path in selected]}")
        else:
            for idx in indices:
                frames = []
                timestamp_str = _format_timestamp(idx / max(fps, 1e-6))
                for view_name, _, cap in caps:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ok, frame = cap.read()
                    if not ok:
                        frames = []
                        break
                    frame = _resize_frame(frame, resize_width)
                    if draw_timestamps or draw_viewposition:
                        ts = timestamp_str if draw_timestamps else None
                        vl = view_name if draw_viewposition else None
                        frame = _draw_timestamp(frame, ts, vl)
                    frames.append(frame)
                if not frames:
                    continue
                merged = _stack_view_frames(frames)
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
            "merge_views": merge_views,
            "merge_mode": merge_mode,
            "merge_layout": "vertical" if merge_mode == "per_frame" else "vertical_views_horizontal_time",
            "video_fps": fps,
            "video_fps_by_view": fps_by_view,
            "total_frames": total_frames,
            "total_frames_by_view": total_frames_by_view,
            "sampled_frames": len(indices),
            "image_parts": len(parts),
            "max_frames": max_frames,
            "frame_range": [start, end],
            "jpeg_quality": jpeg_quality,
            "draw_timestamps": draw_timestamps,
            "draw_viewposition": draw_viewposition,
            "min_api_frames": min_api_frames,
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
    parser.add_argument("--max-frames", type=int, default=None, help="Maximum sampled frames. Defaults to the selected stage setting.")
    parser.add_argument("--merge-views", action=argparse.BooleanOptionalAction, default=None, help="Whether to merge selected multi-view frames. Defaults to the selected stage setting.")
    parser.add_argument("--merge-mode", choices=["per_frame", "timeline_grid"], default=None, help="Multi-view merge mode. Defaults to the selected stage mode.")
    parser.add_argument("--log-level", help="Override config logging.level for this debug run.")
    parser.add_argument("--frame-start", type=int, default=0, help="Inclusive start frame index.")
    parser.add_argument("--frame-end", type=int, default=None, help="Inclusive end frame index.")
    parser.add_argument(
        "--stage",
        choices=["scene", "analysis", "refinement"],
        default="refinement",
        help="Stage defaults to use when --resize-width is not provided.",
    )
    parser.add_argument("--resize-width", type=int, help="Per-view resize width before merge.")
    parser.add_argument("--scene-resize-width", type=int, default=DEFAULT_SCENE_RESIZE_WIDTH)
    parser.add_argument("--analysis-resize-width", type=int, default=DEFAULT_ANALYSIS_RESIZE_WIDTH)
    parser.add_argument("--refinement-resize-width", type=int, default=DEFAULT_REFINEMENT_RESIZE_WIDTH)
    parser.add_argument("--jpeg-quality", type=int, default=None, help="JPEG quality. Defaults to the selected stage setting.")
    parser.add_argument("--min-api-frames", type=int, default=None, help="Minimum frames to send when the clip is long enough. Defaults to the selected stage setting.")
    parser.add_argument(
        "--view-names",
        default=None,
        help="Comma-separated view names to select. Defaults to the selected stage setting; empty string means first input view.",
    )
    parser.add_argument(
        "--draw-timestamps",
        type=_parse_cli_bool,
        default=None,
        help="Whether to draw black-background white timestamps.",
    )
    parser.add_argument(
        "--draw-viewposition",
        type=_parse_cli_bool,
        default=None,
        help="Whether to overlay view/camera name on each frame before merging.",
    )
    parser.add_argument(
        "--merge-length",
        type=int,
        default=None,
        help="Max time columns in timeline_grid mode; 0 means unlimited. Defaults to the selected stage setting.",
    )
    args = parser.parse_args()
    configure_logging(level=args.log_level) if args.log_level else configure_logging()

    if args.view_names is None:
        if args.stage == "scene":
            view_names = DEFAULT_SCENE_MERGE_VIEW_NAMES
        elif args.stage == "analysis":
            view_names = DEFAULT_ANALYSIS_MERGE_VIEW_NAMES
        else:
            view_names = DEFAULT_REFINEMENT_MERGE_VIEW_NAMES
    else:
        view_names = [item.strip() for item in args.view_names.split(",") if item.strip()]
    video_path = _load_debug_video_path(args)
    resize_width = args.resize_width
    if resize_width is None:
        if args.stage == "scene":
            resize_width = args.scene_resize_width
        elif args.stage == "analysis":
            resize_width = args.analysis_resize_width
        else:
            resize_width = args.refinement_resize_width
    target_fps = args.target_fps
    if target_fps is None:
        if args.stage == "scene":
            target_fps = DEFAULT_SCENE_FPS
        elif args.stage == "analysis":
            target_fps = DEFAULT_ANALYSIS_FPS
        else:
            target_fps = DEFAULT_REFINEMENT_FPS
    max_frames = args.max_frames
    if max_frames is None:
        if args.stage == "scene":
            max_frames = DEFAULT_SCENE_MAX_FRAMES
        elif args.stage == "analysis":
            max_frames = DEFAULT_ANALYSIS_MAX_FRAMES
        else:
            max_frames = DEFAULT_REFINEMENT_MAX_FRAMES
    jpeg_quality = args.jpeg_quality
    if jpeg_quality is None:
        if args.stage == "scene":
            jpeg_quality = DEFAULT_SCENE_JPEG_QUALITY
        elif args.stage == "analysis":
            jpeg_quality = DEFAULT_ANALYSIS_JPEG_QUALITY
        else:
            jpeg_quality = DEFAULT_REFINEMENT_JPEG_QUALITY
    min_api_frames = args.min_api_frames
    if min_api_frames is None:
        if args.stage == "scene":
            min_api_frames = DEFAULT_SCENE_MIN_API_FRAMES
        elif args.stage == "analysis":
            min_api_frames = DEFAULT_ANALYSIS_MIN_API_FRAMES
        else:
            min_api_frames = DEFAULT_REFINEMENT_MIN_API_FRAMES
    draw_timestamps = args.draw_timestamps
    if draw_timestamps is None:
        if args.stage == "scene":
            draw_timestamps = DEFAULT_SCENE_DRAW_TIMESTAMPS
        elif args.stage == "analysis":
            draw_timestamps = DEFAULT_ANALYSIS_DRAW_TIMESTAMPS
        else:
            draw_timestamps = DEFAULT_REFINEMENT_DRAW_TIMESTAMPS
    draw_viewposition = args.draw_viewposition
    if draw_viewposition is None:
        if args.stage == "scene":
            draw_viewposition = DEFAULT_SCENE_DRAW_VIEWPOSITION
        elif args.stage == "analysis":
            draw_viewposition = DEFAULT_ANALYSIS_DRAW_VIEWPOSITION
        else:
            draw_viewposition = DEFAULT_REFINEMENT_DRAW_VIEWPOSITION
    merge_views = args.merge_views
    if merge_views is None:
        if args.stage == "scene":
            merge_views = DEFAULT_SCENE_MERGE_VIEWS
        elif args.stage == "analysis":
            merge_views = DEFAULT_ANALYSIS_MERGE_VIEWS
        else:
            merge_views = DEFAULT_REFINEMENT_MERGE_VIEWS
    merge_mode = args.merge_mode
    if merge_mode is None:
        if args.stage == "scene":
            merge_mode = DEFAULT_SCENE_MERGE_MODE
        elif args.stage == "analysis":
            merge_mode = DEFAULT_ANALYSIS_MERGE_MODE
        else:
            merge_mode = DEFAULT_REFINEMENT_MERGE_MODE
    merge_length = args.merge_length
    if merge_length is None:
        if args.stage == "scene":
            merge_length = DEFAULT_SCENE_MERGE_LENGTH
        elif args.stage == "analysis":
            merge_length = DEFAULT_ANALYSIS_MERGE_LENGTH
        else:
            merge_length = DEFAULT_REFINEMENT_MERGE_LENGTH
    logger.info("merge_length=%s (from %s)", merge_length, "CLI" if args.merge_length is not None else "config")
    parts, meta = load_video_or_views_as_image_parts(
        video_path,
        target_fps=target_fps,
        max_frames=max_frames,
        frame_start=args.frame_start,
        frame_end=args.frame_end,
        resize_width=resize_width,
        jpeg_quality=jpeg_quality,
        draw_timestamps=draw_timestamps,
        draw_viewposition=draw_viewposition,
        min_api_frames=min_api_frames,
        merge_length=merge_length,
        view_names=view_names,
        merge_views=merge_views,
        merge_mode=merge_mode,
    )

    output_dir = Path(args.output_dir)
    saved = _save_debug_parts(parts, output_dir)
    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved debug frames count=%s output_dir=%s metadata=%s", len(saved), output_dir, meta_path)
    print(json.dumps({"saved_frames": saved, "metadata": str(meta_path), **meta}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
