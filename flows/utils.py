"""Small helpers shared by named annotation flows."""

from __future__ import annotations

from importlib import import_module
import json
import logging
import time
from typing import Any

from ..utils.api_client import call_vlm, extract_json_from_response
from ..utils.config import (
    DEFAULT_MODEL,
    DEFAULT_PROMPT_LANGUAGE,
    DEFAULT_VLM_TEMPERATURE,
    DEFAULT_VLM_TOP_K,
    DEFAULT_VLM_TOP_P,
)
from ..utils.results import StageResult


logger = logging.getLogger(__name__)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def as_str_list(value: Any) -> list[str]:
    return [str(item).strip() for item in as_list(value) if str(item).strip()]


def normalize_prompt_language(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "zh": "cn",
        "zh_cn": "cn",
        "chinese": "cn",
        "english": "en",
    }
    text = aliases.get(text, text)
    return text if text in {"cn", "en"} else "cn"


def load_prompt_package(prompt_language: str = DEFAULT_PROMPT_LANGUAGE):
    language = normalize_prompt_language(prompt_language)
    package_name = "prompts.prompts_cn" if language == "cn" else "prompts.prompts_en"
    return import_module(f"..{package_name}", package=__package__)


def normalize_robot_type(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "single": "single_arm",
        "single_arm_robot": "single_arm",
        "one_arm": "single_arm",
        "dual_arm": "bimanual",
        "dual_arms": "bimanual",
        "two_arm": "bimanual",
        "two_arms": "bimanual",
        "bimanual_robot": "bimanual",
        "mobile": "mobile_manipulator",
        "mobile_robot": "mobile_manipulator",
        "mobile_manipulator_robot": "mobile_manipulator",
    }
    text = aliases.get(text, text)
    allowed = {"single_arm", "bimanual", "mobile_manipulator", "unknown"}
    return text if text in allowed else "unknown"


def default_executor_for_robot_type(robot_type: str) -> str:
    if robot_type == "single_arm":
        return "single"
    if robot_type == "mobile_manipulator":
        return "arm"
    return "unknown"


def normalize_executor(value: Any, robot_type: str) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "left_arm": "left",
        "right_arm": "right",
        "both_arms": "both",
        "dual": "both",
        "bimanual": "both",
        "single_arm": "single",
        "robot_arm": "arm",
        "manipulator": "arm",
        "mobile_base": "base",
        "chassis": "base",
    }
    text = aliases.get(text, text)
    allowed = {"left", "right", "both", "single", "base", "arm", "unknown"}
    return text if text in allowed else default_executor_for_robot_type(robot_type)


def _action_items_from_text(text: str, robot_type: str) -> list[dict[str, str]]:
    text = text.strip()
    if not text:
        return []

    items: list[dict[str, str]] = []
    chunks = [chunk.strip() for chunk in text.split(";") if chunk.strip()]
    for chunk in chunks:
        lowered = chunk.lower()
        if ":" in chunk:
            prefix, action = chunk.split(":", 1)
            executor = normalize_executor(prefix, robot_type)
            action = action.strip()
        elif lowered.startswith("left arm "):
            executor = "left"
            action = chunk[len("left arm ") :].strip()
        elif lowered.startswith("right arm "):
            executor = "right"
            action = chunk[len("right arm ") :].strip()
        else:
            executor = default_executor_for_robot_type(robot_type)
            action = chunk
        if action:
            items.append({"executor": executor, "action": action, "object": ""})
    return items


def normalize_action_sequence(value: Any, robot_type: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for item in as_list(value):
        if isinstance(item, dict):
            action = str(item.get("action") or item.get("verb") or item.get("name") or "").strip()
            executor = normalize_executor(item.get("executor", item.get("arm")), robot_type)
            obj = str(item.get("object", "") or "").strip()
            if action:
                items.append({"executor": executor, "action": action, "object": obj})
        else:
            items.extend(_action_items_from_text(str(item), robot_type))
    return items


def _timestamp_value(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def normalize_timestamped_action_sequence(
    value: Any,
    fallback_actions: list[dict[str, str]],
    robot_type: str,
) -> list[dict[str, str]]:
    """Align refinement timestamps with the analysis action sequence."""
    raw_items = as_list(value)
    normalized: list[dict[str, str]] = []
    total = max(len(raw_items), len(fallback_actions))
    for index in range(total):
        fallback = fallback_actions[index] if index < len(fallback_actions) else {}
        raw = raw_items[index] if index < len(raw_items) else {}
        raw_dict = raw if isinstance(raw, dict) else {}

        action = str(raw_dict.get("action") or fallback.get("action", "")).strip()
        if not action:
            continue
        executor = normalize_executor(raw_dict.get("executor", fallback.get("executor")), robot_type)
        obj = str(raw_dict.get("object") or fallback.get("object", "") or "").strip()
        normalized.append(
            {
                "executor": executor,
                "action": action,
                "object": obj,
                "start_time": _timestamp_value(raw_dict, "start_time", "startTime", "starttime"),
                "end_time": _timestamp_value(raw_dict, "end_time", "endTime", "endtime"),
            }
        )
    return normalized


def normalize_scene_context(value: Any, meta: dict[str, Any]) -> dict[str, Any]:
    """Normalize scene-stage output and fill a minimal stable context if missing."""
    raw = value if isinstance(value, dict) else {}
    views = [str(view) for view in meta.get("selected_views", [])]
    primary_view = str(raw.get("primary_view") or (views[0] if views else "unknown")).strip()
    try:
        num_arms = int(raw.get("num_arms") or 0)
    except (TypeError, ValueError):
        num_arms = 0
    context: dict[str, Any] = {
        "primary_view": primary_view,
        "spatial_reference_rule": str(
            raw.get("spatial_reference_rule")
            or "All spatial names such as left/right/front/back are defined from the primary view."
        ).strip(),
        "num_arms": num_arms,
        "arms": [],
        "task_objects": [],
        "background_objects": [],
        "view_context": {},
    }

    for item in as_list(raw.get("arms")):
        if not isinstance(item, dict):
            continue
        arm_id = str(item.get("arm_id") or "").strip()
        if not arm_id:
            continue
        context["arms"].append(
            {
                "arm_id": arm_id,
                "description": str(item.get("description") or "").strip(),
                "spatial_reference": str(item.get("spatial_reference") or "primary_view").strip(),
                "main_workspace": str(item.get("main_workspace") or "").strip(),
                "handled_objects": as_str_list(item.get("handled_objects")),
                "best_observation_views": [
                    {
                        "view_name": str(view.get("view_name") or "").strip(),
                        "reason": str(view.get("reason") or "").strip(),
                    }
                    for view in as_list(item.get("best_observation_views"))
                    if isinstance(view, dict) and str(view.get("view_name") or "").strip()
                ],
            }
        )

    if not context["num_arms"]:
        context["num_arms"] = len(context["arms"])

    for key in ("task_objects", "background_objects"):
        for item in as_list(raw.get(key)):
            if not isinstance(item, dict):
                continue
            object_id = str(item.get("object_id") or "").strip()
            if not object_id:
                continue
            context[key].append(
                {
                    "object_id": object_id,
                    "description": str(item.get("description") or object_id).strip(),
                    "role": str(item.get("role") or ("background" if key == "background_objects" else "")).strip(),
                }
            )

    raw_view_context = raw.get("view_context")
    if isinstance(raw_view_context, dict):
        for view_name, item in raw_view_context.items():
            if isinstance(item, dict):
                description = str(item.get("description") or "").strip()
            else:
                description = str(item or "").strip()
            context["view_context"][str(view_name)] = {"description": description}

    for index, view in enumerate(views):
        context["view_context"].setdefault(
            view,
            {
                "description": (
                    "primary view; spatial names are based on this view"
                    if index == 0
                    else "auxiliary view; use it to verify occlusion, contact, and depth without renaming arms"
                )
            },
        )

    return context


CN_OBJECT_TRANSLATIONS = {
    "laptop": "笔记本电脑",
    "laptop stand": "笔记本电脑支架",
    "computer stand": "电脑支架",
    "stand": "支架",
    "cup": "杯子",
    "paper cup": "纸杯",
    "bowl": "碗",
    "ceramic bowl": "陶瓷碗",
    "plate": "盘子",
    "table": "桌子",
    "box": "盒子",
    "drawer": "抽屉",
    "door": "门",
    "lid": "盖子",
    "handle": "把手",
}


def translate_object_for_prompt_language(value: Any, prompt_language: str) -> str:
    text = str(value or "").strip()
    if normalize_prompt_language(prompt_language) != "cn" or not text:
        return text
    return CN_OBJECT_TRANSLATIONS.get(text.lower(), text)


def localize_action_sequence_objects(items: list[dict[str, str]], prompt_language: str) -> list[dict[str, str]]:
    if normalize_prompt_language(prompt_language) != "cn":
        return items
    localized = []
    for item in items:
        updated = dict(item)
        updated["object"] = translate_object_for_prompt_language(updated.get("object", ""), prompt_language)
        localized.append(updated)
    return localized


def describe_view_layout(meta: dict[str, Any], prompt_language: str) -> str:
    language = normalize_prompt_language(prompt_language)
    views = [str(view) for view in meta.get("selected_views", [])]
    input_mode = meta.get("input_mode", "single_view")
    merge_mode = meta.get("merge_mode", "per_frame")
    if input_mode == "merged_views" and len(views) > 1:
        if merge_mode == "timeline_grid":
            if language == "cn":
                rows = "\n".join(f"- Y 方向第 {i + 1} 行：{view}" for i, view in enumerate(views))
                return (
                    "每张输入图片是一个时间轴多视角拼图。Y 方向表示不同视角，X 方向表示采样时间从左到右推进。"
                    "左侧标注视角名称，顶部标注每一列对应的时间戳；每个单元格也可能根据当前阶段配置带有帧内时间戳。"
                    "视角行顺序如下：\n"
                    f"{rows}\n"
                    "第 1 行/第一个被选中的视角是 primary view。left/right/front/back/far/close 等空间命名必须以 primary view 为准；"
                    "其他视角只用于辅助确认遮挡、接触和深度关系。不要把 Y 方向的不同行理解为时间先后；动作前后顺序只沿 X 方向时间变化判断。"
                )
            rows = "\n".join(f"- Y row {i + 1}: {view}" for i, view in enumerate(views))
            return (
                "Each input image is a timeline multi-view grid. The Y axis contains different views and the X axis "
                "contains sampled time moving from left to right. The left side labels view names and the top labels "
                "the timestamp of each time column; each cell may also contain an in-frame timestamp depending on "
                "the current stage setting. View rows are:\n"
                f"{rows}\n"
                "Y row 1 / the first selected view is the primary view. Spatial names such as left/right/front/back/"
                "far/close must use the primary view as reference. Use other views only to verify occlusion, contact, "
                "and depth. Do not interpret different Y rows as temporal order; temporal order follows the X axis."
            )
        if language == "cn":
            rows = "\n".join(f"- 第 {i + 1} 行：{view}" for i, view in enumerate(views))
            return (
                "每张输入图片都是同一时间戳的多视角帧竖向拼接图。拼接前，每个视角图像会先按当前阶段配置的 resize_width 单独缩放。"
                "拼接后从上到下的行顺序如下：\n"
                f"{rows}\n"
                "第 1 行/第一个被选中的视角是 primary view。描述 left/right/front/back/far/close 等空间方向时，"
                "必须以 primary view 为准；其他视角只用于辅助确认遮挡、接触和深度关系。不要把不同行误认为时间先后。"
            )
        rows = "\n".join(f"- Row {i + 1}: {view}" for i, view in enumerate(views))
        return (
            "Each input image is a vertical concatenation of frames from multiple views at the same timestamp. "
            "Before concatenation, each view is resized independently according to the current stage's resize_width. "
            "The row order from top to bottom is:\n"
            f"{rows}\n"
            "Row 1 / the first selected view is the primary view. When describing spatial directions such as "
            "left/right/front/back/far/close, use the primary view as the reference frame; use other views only "
            "to confirm occlusion, contact, and depth relations. Use all rows as simultaneous views of the same "
            "moment; do not interpret different rows as temporal order. Order actions by their start time: the "
            "action that starts earlier must appear earlier."
        )
    view = views[0] if views else "unknown"
    if language == "cn":
        return f"每张输入图片来自单一视角：{view}。不同图片之间才表示按时间采样的帧序列。"
    return f"Each input image comes from a single view: {view}. Different images represent the temporal frame sequence."

def numbered_text(items: list[str]) -> str:
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items))


def instruction_from_steps(steps: list[str]) -> str:
    return " ".join(f"({i + 1}) {step}" for i, step in enumerate(steps))


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def make_stage(
    name: str,
    raw_response: str,
    token_usage: dict[str, int],
    *,
    fallback: dict[str, Any] | None = None,
) -> StageResult:
    parsed = extract_json_from_response(raw_response) or fallback or {}
    if parsed:
        logger.debug("Stage %s JSON parsed keys=%s", name, list(parsed.keys()))
    else:
        logger.warning("Stage %s produced no parseable JSON", name)
    return StageResult(
        name=name,
        output=parsed,
        raw_response=raw_response,
        success=bool(parsed),
        token_usage=token_usage,
        error=None if parsed else "No JSON object could be parsed from model response.",
    )


def call_json_stage(
    client,
    *,
    name: str,
    parts: list[dict[str, Any]],
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    fallback: dict[str, Any] | None = None,
    max_tokens: int = 0,
    temperature: float = DEFAULT_VLM_TEMPERATURE,
    top_p: float = DEFAULT_VLM_TOP_P,
    top_k: int = DEFAULT_VLM_TOP_K,
) -> StageResult:
    logger.info(
        "Stage %s start images=%s max_tokens=%s temperature=%s top_p=%s top_k=%s",
        name,
        len(parts),
        max_tokens,
        temperature,
        top_p,
        top_k,
    )
    start = time.perf_counter()
    raw, usage = call_vlm(
        client,
        parts,
        system_prompt,
        user_prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
    )
    stage = make_stage(name, raw, usage, fallback=fallback)
    logger.info(
        "Stage %s done success=%s elapsed=%.2fs prompt_tokens=%s completion_tokens=%s total_tokens=%s",
        name,
        stage.success,
        time.perf_counter() - start,
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
        usage.get("total_tokens", 0),
    )
    return stage

