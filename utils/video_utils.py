"""Video frame sampling utilities for VLM requests."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from .config import DEFAULT_JPEG_QUALITY, DEFAULT_MAX_FRAMES, DEFAULT_RESIZE_WIDTH, MIN_API_FRAMES


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


def load_video_as_image_parts(
    video_path: str | Path,
    *,
    target_fps: float,
    max_frames: int = DEFAULT_MAX_FRAMES,
    frame_start: int = 0,
    frame_end: int | None = None,
    resize_width: int = DEFAULT_RESIZE_WIDTH,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load sampled video frames as OpenAI image_url parts."""
    import cv2

    path = str(video_path)
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
            b64 = _encode_jpeg(frame, resize_width, jpeg_quality)
            parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

        if not parts:
            raise RuntimeError(f"No frames sampled from {path}")

        return parts, {
            "video_path": path,
            "video_fps": fps,
            "total_frames": total_frames,
            "sampled_frames": len(parts),
            "frame_range": [start, end],
        }
    finally:
        cap.release()


def labelled_view_parts(view_name: str, parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefix image parts with a text label naming the view."""
    return [{"type": "text", "text": f"[View: {view_name}]"}, *parts]
