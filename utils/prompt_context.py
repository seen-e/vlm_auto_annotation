"""Prompt context helpers for current stage templates."""

from __future__ import annotations

import json
from typing import Any


def normalize_prompt_language(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {"zh": "cn", "zh_cn": "cn", "chinese": "cn", "english": "en"}
    text = aliases.get(text, text)
    return text if text in {"cn", "en"} else "cn"


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def describe_view_layout(meta: dict[str, Any], prompt_language: str) -> str:
    language = normalize_prompt_language(prompt_language)
    views = [str(view) for view in meta.get("selected_views", [])]
    source_type = meta.get("source_type") or meta.get("input_mode", "single_view")
    merge_mode = meta.get("merge_mode", "per_frame")
    if source_type in {"multi_view", "merged_views"} and len(views) > 1:
        if merge_mode == "timeline_grid":
            if language == "cn":
                rows = "\n".join(f"- Y 方向第 {i + 1} 行：{view}" for i, view in enumerate(views))
                return (
                    "每张输入图片是时间轴多视角拼图。Y 方向表示不同视角，X 方向表示采样时间从左到右推进。"
                    "第一个被选中的视角是 primary view，left/right/front/back 等空间命名必须以 primary view 为准。\n"
                    f"{rows}"
                )
            rows = "\n".join(f"- Y row {i + 1}: {view}" for i, view in enumerate(views))
            return (
                "Each input image is a timeline multi-view grid. The Y axis contains views and the X axis contains "
                "sampled time from left to right. The first selected view is the primary view for spatial names.\n"
                f"{rows}"
            )
        if language == "cn":
            rows = "\n".join(f"- 第 {i + 1} 行：{view}" for i, view in enumerate(views))
            return (
                "每张输入图片都是同一时间戳的多视角帧竖向拼接图。第一个被选中的视角是 primary view，"
                "left/right/front/back 等空间命名必须以 primary view 为准。\n"
                f"{rows}"
            )
        rows = "\n".join(f"- Row {i + 1}: {view}" for i, view in enumerate(views))
        return (
            "Each input image is a vertical concatenation of multiple views at the same timestamp. "
            "The first selected view is the primary view for spatial names.\n"
            f"{rows}"
        )
    view = views[0] if views else "unknown"
    if language == "cn":
        return f"每张输入图片来自单一视角：{view}。该视角就是 primary view。"
    return f"Each input image comes from a single view: {view}. This view is the primary view."
