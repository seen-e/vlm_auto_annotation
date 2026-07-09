"""Video frame sampling utilities for VLM requests."""

from __future__ import annotations

import base64
import io
import json
import logging
from pathlib import Path
import tempfile
import time
from typing import Any, Literal


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
    mode = str(value or "per_frame").strip().lower().replace("-", "_")
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
    merge_view_names: list[str] | None,
    *,
    merge_views: bool = True,
) -> list[tuple[str, str]]:
    if isinstance(video_path, dict):
        available = [(str(name), str(path)) for name, path in video_path.items()]
        if not merge_views:
            return available[:1]
        if merge_view_names:
            by_name = dict(available)
            missing = [name for name in merge_view_names if name not in by_name]
            if missing:
                raise KeyError(f"Requested view(s) not found: {missing}. Available views: {list(by_name)}")
            return [(name, by_name[name]) for name in merge_view_names]
        return available[:1]
    if isinstance(video_path, (list, tuple)):
        available = [(Path(path).parent.name, str(path)) for path in video_path]
        if not merge_views:
            return available[:1]
        if merge_view_names:
            by_name = dict(available)
            missing = [name for name in merge_view_names if name not in by_name]
            if missing:
                raise KeyError(f"Requested view(s) not found: {missing}. Available views: {list(by_name)}")
            return [(name, by_name[name]) for name in merge_view_names]
        return available[:1]
    return [(Path(video_path).parent.name, str(video_path))]


def _build_timeline_grid(
    *,
    cells_by_time: list[list[Any]],
    view_labels: list[str],
    timestamps: list[str],
) -> Any:
    import cv2
    import numpy as np

    if not cells_by_time:
        raise ValueError("No frames to build timeline grid")

    flat_cells = [frame for frames in cells_by_time for frame in frames]
    cell_w = max(frame.shape[1] for frame in flat_cells)
    cell_h = max(frame.shape[0] for frame in flat_cells)
    left_header_w = max(180, min(360, 12 * max((len(name) for name in view_labels), default=8)))
    top_header_h = 36

    rows = len(view_labels)
    cols = len(cells_by_time)
    canvas_h = top_header_h + rows * cell_h
    canvas_w = left_header_w + cols * cell_w
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

    for col, timestamp in enumerate(timestamps):
        x = left_header_w + col * cell_w
        _draw_label(canvas, f"t={timestamp}", (x + 8, 24), scale=0.55, thickness=1)
        cv2.line(canvas, (x, 0), (x, canvas_h), (70, 70, 70), 1)

    for row, view_name in enumerate(view_labels):
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


def _processed_meta(
    *,
    video_path: Any,
    selected: list[tuple[str, str]],
    source_type: str,
    fps: float,
    target_fps: float,
    total_frames: int,
    sampled_frame_count: int,
    processed_frame_count: int,
    max_frames: int,
    frame_start: int,
    frame_end: int,
    resize_width: int,
    jpeg_quality: int,
    min_api_frames: int,
    merge_views: bool,
    merge_view_names: list[str],
    merge_mode: str,
    merge_length: int,
    draw_timestamps: bool,
    draw_viewposition: bool,
    elapsed: float,
    **extra: Any,
) -> dict[str, Any]:
    meta = {
        "video_path": video_path,
        "source_type": source_type,
        "fps": fps,
        "video_fps": fps,
        "target_fps": target_fps,
        "total_frames": total_frames,
        "sampled_frame_count": sampled_frame_count,
        "sampled_frames": sampled_frame_count,
        "processed_frame_count": processed_frame_count,
        "max_frames": max_frames,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "frame_range": [frame_start, frame_end],
        "resize_width": resize_width,
        "jpeg_quality": jpeg_quality,
        "min_api_frames": min_api_frames,
        "merge_views": merge_views,
        "merge_view_names": merge_view_names,
        "selected_views": [name for name, _ in selected],
        "merge_mode": merge_mode,
        "merge_length": merge_length,
        "draw_timestamps": draw_timestamps,
        "draw_viewposition": draw_viewposition,
        "load_elapsed_seconds": round(elapsed, 3),
    }
    meta.update(extra)
    return meta


def _sample_indices_for_range(
    *,
    total_frames: int,
    fps: float,
    target_fps: float,
    max_frames: int,
    frame_start: int,
    frame_end: int | None,
    min_api_frames: int,
) -> tuple[list[int], int, int]:
    start = max(0, int(frame_start or 0))
    end = min(total_frames, int(frame_end) + 1) if frame_end is not None else total_frames
    span = max(0, end - start)
    local_indices = _sample_indices(span, fps, target_fps, max_frames)
    indices = [start + i for i in local_indices]
    if 0 < len(indices) < 2 and span >= 2:
        step = (span - 1) / max(2 - 1, 1)
        indices = sorted(set(start + int(round(i * step)) for i in range(2)))
    return indices, start, end


def _read_preprocessed_frame(
    cap,
    *,
    frame_index: int,
    fps: float,
    resize_width: int,
    draw_timestamps: bool,
    draw_viewposition: bool,
    view_name: str | None,
):
    import cv2

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    if not ok:
        return None
    frame = _resize_frame(frame, resize_width)
    if draw_timestamps or draw_viewposition:
        timestamp = _format_timestamp(frame_index / max(fps, 1e-6)) if draw_timestamps else None
        label = view_name if draw_viewposition else None
        frame = _draw_timestamp(frame, timestamp, label)
    return frame


def _load_video_or_views_as_processed_frames(
    video_path: str | Path | list[str | Path] | dict[str, str | Path],
    *,
    target_fps: float,
    max_frames: int,
    frame_start: int,
    frame_end: int | None,
    resize_width: int,
    jpeg_quality: int,
    draw_timestamps: bool,
    draw_viewposition: bool,
    min_api_frames: int,
    merge_length: int,
    merge_view_names: list[str] | None,
    merge_views: bool,
    merge_mode: str,
) -> tuple[list[Any], dict[str, Any]]:
    """Return processed BGR frames shared by image and video media encoders."""
    import cv2

    start_time = time.perf_counter()
    merge_mode = _normalize_merge_mode(merge_mode)
    selected = _select_video_views(video_path, merge_view_names or None, merge_views=merge_views)

    if len(selected) == 1:
        view_name, path = selected[0]
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Could not open video: {path}")
        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
            indices, start, end = _sample_indices_for_range(
                total_frames=total_frames,
                fps=fps,
                target_fps=target_fps,
                max_frames=max_frames,
                frame_start=frame_start,
                frame_end=frame_end,
        min_api_frames=min_api_frames,
            )
            frames = []
            for idx in indices:
                frame = _read_preprocessed_frame(
                    cap,
                    frame_index=idx,
                    fps=fps,
                    resize_width=resize_width,
                    draw_timestamps=draw_timestamps,
                    draw_viewposition=draw_viewposition,
                    view_name=view_name,
                )
                if frame is not None:
                    frames.append(frame)
            if not frames:
                raise RuntimeError(f"No frames sampled from {path}")
            elapsed = time.perf_counter() - start_time
            return frames, _processed_meta(
                video_path=path,
                selected=selected,
                source_type="single_view",
                fps=fps,
                target_fps=target_fps,
                total_frames=total_frames,
                sampled_frame_count=len(indices),
                processed_frame_count=len(frames),
                max_frames=max_frames,
                frame_start=start,
                frame_end=end,
                resize_width=resize_width,
                jpeg_quality=jpeg_quality,
        min_api_frames=min_api_frames,
                merge_views=merge_views,
                merge_view_names=[view_name],
                merge_mode="single_view",
                merge_length=merge_length,
                draw_timestamps=draw_timestamps,
                draw_viewposition=draw_viewposition,
                elapsed=elapsed,
            )
        finally:
            cap.release()

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
        indices, start, end = _sample_indices_for_range(
            total_frames=total_frames,
            fps=fps,
            target_fps=target_fps,
            max_frames=max_frames,
            frame_start=frame_start,
            frame_end=frame_end,
        min_api_frames=min_api_frames,
        )

        frames_out: list[Any] = []
        if merge_mode == "timeline_grid":
            chunks = [indices[i : i + merge_length] for i in range(0, len(indices), merge_length)] if merge_length > 0 else [indices]
            view_order = [name for name, _, _ in caps]
            for chunk in chunks:
                cells_by_time: list[list[Any]] = []
                timestamps: list[str] = []
                for idx in chunk:
                    frames = []
                    for view_name, _, cap in caps:
                        frame = _read_preprocessed_frame(
                            cap,
                            frame_index=idx,
                            fps=fps,
                            resize_width=resize_width,
                            draw_timestamps=draw_timestamps,
                            draw_viewposition=draw_viewposition,
                            view_name=view_name,
                        )
                        if frame is None:
                            frames = []
                            break
                        frames.append(frame)
                    if frames:
                        cells_by_time.append(frames)
                        timestamps.append(_format_timestamp(idx / max(fps, 1e-6)))
                if cells_by_time:
                    frames_out.append(_build_timeline_grid(cells_by_time=cells_by_time, view_labels=view_order, timestamps=timestamps))
        else:
            for idx in indices:
                frames = []
                for view_name, _, cap in caps:
                    frame = _read_preprocessed_frame(
                        cap,
                        frame_index=idx,
                        fps=fps,
                        resize_width=resize_width,
                        draw_timestamps=draw_timestamps,
                        draw_viewposition=draw_viewposition,
                        view_name=view_name,
                    )
                    if frame is None:
                        frames = []
                        break
                    frames.append(frame)
                if frames:
                    frames_out.append(_stack_view_frames(frames))

        if not frames_out:
            raise RuntimeError(f"No frames sampled from selected views: {[path for _, path in selected]}")

        elapsed = time.perf_counter() - start_time
        return frames_out, _processed_meta(
            video_path={name: path for name, path, _ in caps},
            selected=[(name, path) for name, path, _ in caps],
            source_type="multi_view",
            fps=fps,
            target_fps=target_fps,
            total_frames=total_frames,
            sampled_frame_count=len(indices),
            processed_frame_count=len(frames_out),
            max_frames=max_frames,
            frame_start=start,
            frame_end=end,
            resize_width=resize_width,
            jpeg_quality=jpeg_quality,
        min_api_frames=min_api_frames,
            merge_views=merge_views,
            merge_view_names=[name for name, _, _ in caps],
            merge_mode=merge_mode,
            merge_length=merge_length,
            draw_timestamps=draw_timestamps,
            draw_viewposition=draw_viewposition,
            elapsed=elapsed,
            video_fps_by_view=fps_by_view,
            total_frames_by_view=total_frames_by_view,
            merge_layout="vertical" if merge_mode == "per_frame" else "vertical_views_horizontal_time",
        )
    finally:
        for _, _, cap in caps:
            cap.release()


def _encode_frames_as_image_parts(frames: list[Any], *, jpeg_quality: int) -> list[dict[str, Any]]:
    return [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_encode_jpeg_preprocessed(frame, jpeg_quality)}"}}
        for frame in frames
    ]


def _pad_frame_to_even_size(frame):
    h, w = frame.shape[:2]
    return _pad_to_size(frame, w + (w % 2), h + (h % 2))


def _encode_frames_as_video_part(frames: list[Any], *, fps: float, suffix: str = ".mp4") -> dict[str, Any]:
    import cv2

    if not frames:
        raise ValueError("No frames to encode as video")
    normalized = [_pad_frame_to_even_size(frame) for frame in frames]
    width = max(frame.shape[1] for frame in normalized)
    height = max(frame.shape[0] for frame in normalized)
    normalized = [_pad_to_size(frame, width, height) for frame in normalized]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        writer = cv2.VideoWriter(str(tmp_path), fourcc, max(float(fps), 1.0), (width, height))
        if not writer.isOpened():
            raise RuntimeError("cv2.VideoWriter failed to open temporary MP4")
        try:
            for frame in normalized:
                writer.write(frame)
        finally:
            writer.release()
        b64 = base64.b64encode(tmp_path.read_bytes()).decode("utf-8")
        return {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{b64}"}}
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def load_video_as_image_parts(
    video_path: str | Path,
    *,
    target_fps: float,
    max_frames: int = 128,
    frame_start: int = 0,
    frame_end: int | None = None,
    resize_width: int = 336,
    jpeg_quality: int = 85,
    draw_timestamps: bool = False,
    draw_viewposition: bool = False,
    view_label: str | None = None,
    min_api_frames: int = 2,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load sampled video frames as OpenAI image_url parts."""
    frames, meta = _load_video_or_views_as_processed_frames(
        video_path,
        target_fps=target_fps,
        max_frames=max_frames,
        frame_start=frame_start,
        frame_end=frame_end,
        resize_width=resize_width,
        jpeg_quality=jpeg_quality,
        draw_timestamps=draw_timestamps,
        draw_viewposition=draw_viewposition,
        min_api_frames=min_api_frames,
        merge_length=0,
        merge_view_names=[view_label] if view_label else None,
        merge_views=False,
        merge_mode="per_frame",
    )
    parts = _encode_frames_as_image_parts(frames, jpeg_quality=jpeg_quality)
    meta["input_mode"] = "image_sequence"
    meta["media_part_count"] = len(parts)
    meta["image_parts"] = len(parts)
    return parts, meta


def load_video_or_views_as_image_parts(
    video_path: str | Path | list[str | Path] | dict[str, str | Path],
    *,
    target_fps: float,
    max_frames: int = 128,
    frame_start: int = 0,
    frame_end: int | None = None,
    resize_width: int = 336,
    jpeg_quality: int = 85,
    draw_timestamps: bool = False,
    draw_viewposition: bool = False,
    min_api_frames: int = 2,
    merge_length: int = 0,
    merge_view_names: list[str] | None = None,
    merge_views: bool = True,
    merge_mode: str = "per_frame",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load one video or time-aligned multi-view videos as image_url parts."""
    frames, meta = _load_video_or_views_as_processed_frames(
        video_path,
        target_fps=target_fps,
        max_frames=max_frames,
        frame_start=frame_start,
        frame_end=frame_end,
        resize_width=resize_width,
        jpeg_quality=jpeg_quality,
        draw_timestamps=draw_timestamps,
        draw_viewposition=draw_viewposition,
        min_api_frames=min_api_frames,
        merge_length=merge_length,
        merge_view_names=merge_view_names,
        merge_views=merge_views,
        merge_mode=merge_mode,
    )
    parts = _encode_frames_as_image_parts(frames, jpeg_quality=jpeg_quality)
    meta.update(
        {
            "input_mode": "image_sequence",
            "media_part_count": len(parts),
            "image_parts": len(parts),
            "video_parts": 0,
        }
    )
    return parts, meta


def load_video_or_views_as_video_parts(
    video_path: str | Path | list[str | Path] | dict[str, str | Path],
    *,
    target_fps: float,
    max_frames: int = 128,
    frame_start: int = 0,
    frame_end: int | None = None,
    resize_width: int = 336,
    jpeg_quality: int = 85,
    draw_timestamps: bool = False,
    draw_viewposition: bool = False,
    min_api_frames: int = 2,
    merge_length: int = 0,
    merge_view_names: list[str] | None = None,
    merge_views: bool = True,
    merge_mode: str = "per_frame",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load one video or multi-view videos as a single video_url part."""
    frames, meta = _load_video_or_views_as_processed_frames(
        video_path,
        target_fps=target_fps,
        max_frames=max_frames,
        frame_start=frame_start,
        frame_end=frame_end,
        resize_width=resize_width,
        jpeg_quality=jpeg_quality,
        draw_timestamps=draw_timestamps,
        draw_viewposition=draw_viewposition,
        min_api_frames=min_api_frames,
        merge_length=merge_length,
        merge_view_names=merge_view_names,
        merge_views=merge_views,
        merge_mode=merge_mode,
    )
    part = _encode_frames_as_video_part(frames, fps=target_fps)
    parts = [part]
    meta.update(
        {
            "input_mode": "video",
            "media_part_count": len(parts),
            "image_parts": 0,
            "video_parts": len(parts),
        }
    )
    return parts, meta


def load_video_or_views_as_media_parts(
    video_path: str | Path | list[str | Path] | dict[str, str | Path],
    *,
    input_mode: Literal["image_sequence", "video"] = "image_sequence",
    target_fps: float,
    max_frames: int = 128,
    frame_start: int = 0,
    frame_end: int | None = None,
    resize_width: int = 336,
    jpeg_quality: int = 85,
    draw_timestamps: bool = False,
    draw_viewposition: bool = False,
    min_api_frames: int = 2,
    merge_length: int = 0,
    merge_view_names: list[str] | None = None,
    merge_views: bool = True,
    merge_mode: str = "per_frame",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Unified media loader for image sequence or direct video VLM inputs."""
    if input_mode == "image_sequence":
        return load_video_or_views_as_image_parts(
            video_path,
            target_fps=target_fps,
            max_frames=max_frames,
            frame_start=frame_start,
            frame_end=frame_end,
            resize_width=resize_width,
            jpeg_quality=jpeg_quality,
            draw_timestamps=draw_timestamps,
            draw_viewposition=draw_viewposition,
            min_api_frames=min_api_frames,
            merge_length=merge_length,
            merge_view_names=merge_view_names,
            merge_views=merge_views,
            merge_mode=merge_mode,
        )
    if input_mode == "video":
        return load_video_or_views_as_video_parts(
            video_path,
            target_fps=target_fps,
            max_frames=max_frames,
            frame_start=frame_start,
            frame_end=frame_end,
            resize_width=resize_width,
            jpeg_quality=jpeg_quality,
            draw_timestamps=draw_timestamps,
            draw_viewposition=draw_viewposition,
            min_api_frames=min_api_frames,
            merge_length=merge_length,
            merge_view_names=merge_view_names,
            merge_views=merge_views,
            merge_mode=merge_mode,
        )
    raise ValueError(f"input_mode must be 'image_sequence' or 'video', got: {input_mode}")

def labelled_view_parts(view_name: str, parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefix image parts with a text label naming the view."""
    return [{"type": "text", "text": f"[View: {view_name}]"}, *parts]


def _strip_data_url(value: str) -> str:
    for prefix in ("data:image/jpeg;base64,", "data:video/mp4;base64,"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def _safe_media_name(value: str) -> str:
    text = str(value).strip() or "episode"
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in text)
    cleaned = cleaned.strip(" .")
    return cleaned or "episode"


def save_processed_media(
    media: list[dict[str, Any]] | list[Any] | str | Path,
    *,
    save_root: str | Path,
    stage_name: str,
    episode_name: str,
    jpeg_quality: int = 85,
) -> list[str]:
    """Save the final media parts sent to one stage."""
    if not save_root:
        raise ValueError("save_root must be non-empty")

    root = Path(save_root)
    safe_episode = _safe_media_name(episode_name)

    if isinstance(media, (str, Path)):
        source_path = Path(media)
        if not source_path.exists():
            raise FileNotFoundError(f"Processed video path not found for stage {stage_name}: {source_path}")
        stage_dir = root / stage_name
        stage_dir.mkdir(parents=True, exist_ok=True)
        output_path = stage_dir / f"{safe_episode}.mp4"
        output_path.write_bytes(source_path.read_bytes())
        logger.info("Saved processed media stage=%s episode=%s path=%s", stage_name, safe_episode, output_path)
        return [str(output_path)]

    if not isinstance(media, list):
        raise TypeError(f"media must be media parts, frame list, or MP4 path; got {type(media).__name__}")
    if not media:
        raise ValueError(f"No processed media to save for stage {stage_name}")

    if not isinstance(media[0], dict):
        output_dir = root / stage_name / safe_episode
        output_dir.mkdir(parents=True, exist_ok=True)
        for frame_path in output_dir.glob("frame_*.jpg"):
            frame_path.unlink()
        saved_frames: list[str] = []
        for index, frame in enumerate(media):
            output_path = output_dir / f"frame_{index:06d}.jpg"
            output_path.write_bytes(base64.b64decode(_encode_jpeg_preprocessed(frame, jpeg_quality)))
            saved_frames.append(str(output_path))
        logger.info("Saved processed media stage=%s episode=%s count=%s dir=%s", stage_name, safe_episode, len(saved_frames), output_dir)
        return saved_frames

    image_parts = [part for part in media if "image_url" in part]
    video_parts = [part for part in media if "video_url" in part]
    if video_parts:
        stage_dir = root / stage_name
        stage_dir.mkdir(parents=True, exist_ok=True)
        output_path = stage_dir / f"{safe_episode}.mp4"
        url = video_parts[0].get("video_url", {}).get("url", "")
        if not url:
            raise ValueError(f"Video part for stage {stage_name} has no video_url.url")
        output_path.write_bytes(base64.b64decode(_strip_data_url(url)))
        logger.info("Saved processed media stage=%s episode=%s path=%s", stage_name, safe_episode, output_path)
        return [str(output_path)]

    output_dir = root / stage_name / safe_episode
    output_dir.mkdir(parents=True, exist_ok=True)
    for frame_path in output_dir.glob("frame_*.jpg"):
        frame_path.unlink()
    saved: list[str] = []
    for index, part in enumerate(image_parts):
        url = part.get("image_url", {}).get("url", "")
        if not url:
            raise ValueError(f"Image part {index} for stage {stage_name} has no image_url.url")
        output_path = output_dir / f"frame_{index:06d}.jpg"
        output_path.write_bytes(base64.b64decode(_strip_data_url(url)))
        saved.append(str(output_path))
    logger.info("Saved processed media stage=%s episode=%s count=%s dir=%s", stage_name, safe_episode, len(saved), output_dir)
    return saved


