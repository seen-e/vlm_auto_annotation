"""Unified media input builder."""

from __future__ import annotations

from typing import Any


def build_media_parts(video_path: Any, stage_config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from ..utils.video_utils import load_video_or_views_as_media_parts

    return load_video_or_views_as_media_parts(
        video_path,
        input_mode=stage_config.get("input_mode", "image_sequence"),
        target_fps=float(stage_config.get("fps", 1.0) or 1.0),
        max_frames=int(stage_config.get("max_frames", 128) or 128),
        resize_width=int(stage_config.get("resize_width", 336) or 336),
        jpeg_quality=int(stage_config.get("jpeg_quality", 85) or 85),
        min_api_frames=int(stage_config.get("min_api_frames", 2) or 2),
        draw_timestamps=bool(stage_config.get("draw_timestamps", False)),
        draw_viewposition=bool(stage_config.get("draw_viewposition", False)),
        merge_length=int(stage_config.get("merge_length", 0) or 0),
        merge_view_names=stage_config.get("merge_view_names"),
        merge_views=bool(stage_config.get("merge_views", True)),
        merge_mode=str(stage_config.get("merge_mode", "per_frame") or "per_frame"),
    )
