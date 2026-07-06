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
from ..utils.schemas import StageResult


logger = logging.getLogger(__name__)
PHASE_PRIMITIVES = {
    "approach",
    "grasp",
    "lift",
    "transfer",
    "place",
    "release",
    "push",
    "pull",
    "rotate",
    "insert",
    "withdraw",
    "open",
    "close",
    "handover",
    "retract",
    "idle",
}
ACTION_TO_PRIMITIVE = {
    "接近": "approach",
    "抓住": "grasp",
    "夹取": "grasp",
    "拿起": "lift",
    "移动": "transfer",
    "拖动": "transfer",
    "放置": "place",
    "释放": "release",
    "推动": "push",
    "拉动": "pull",
    "旋转": "rotate",
    "插入": "insert",
    "拔出": "withdraw",
    "打开": "open",
    "关闭": "close",
    "交接": "handover",
    "撤回": "retract",
    "approach": "approach",
    "navigate": "approach",
    "grasp": "grasp",
    "lift": "lift",
    "move": "transfer",
    "transfer": "transfer",
    "place": "place",
    "release": "release",
    "push": "push",
    "pull": "pull",
    "rotate": "rotate",
    "insert": "insert",
    "withdraw": "withdraw",
    "open": "open",
    "close": "close",
    "handover": "handover",
    "retract": "retract",
    "idle": "idle",
}


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
    package_name = "prompts_cn" if language == "cn" else "prompts"
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
    items: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(value), start=1):
        if isinstance(item, dict):
            action = str(item.get("action") or item.get("verb") or item.get("name") or "").strip()
            executor = normalize_executor(item.get("executor", item.get("arm")), robot_type)
            obj = item.get("object", None)
            target = item.get("target", None)
            event_id = str(item.get("event_id") or item.get("id") or f"E{index:03d}").strip()
            rough_order = item.get("rough_order", index)
            if action:
                items.append(
                    {
                        "event_id": event_id,
                        "executor": executor,
                        "action": action,
                        "object": str(obj).strip() if obj is not None and str(obj).strip() else None,
                        "target": str(target).strip() if target is not None and str(target).strip() else None,
                        "rough_order": int(rough_order) if str(rough_order).isdigit() else index,
                    }
                )
        else:
            for parsed in _action_items_from_text(str(item), robot_type):
                index = len(items) + 1
                parsed.update({"event_id": f"E{index:03d}", "target": None, "rough_order": index})
                if parsed.get("object") == "":
                    parsed["object"] = None
                items.append(parsed)
    return items


def normalize_scene(value: Any, robot_type: str, action_sequence: list[dict[str, Any]]) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    arms = []
    for item in as_list(raw.get("arms")):
        if not isinstance(item, dict):
            continue
        arm_id = normalize_executor(item.get("arm_id", item.get("executor")), robot_type)
        arms.append(
            {
                "arm_id": arm_id,
                "description": str(item.get("description", "") or "").strip(),
                "best_view": str(item.get("best_view", "") or "").strip(),
            }
        )
    if not arms:
        executors = []
        for item in action_sequence:
            executor = item.get("executor", default_executor_for_robot_type(robot_type))
            if executor not in executors:
                executors.append(executor)
        arms = [{"arm_id": executor, "description": "", "best_view": ""} for executor in executors]

    objects_by_id: dict[str, dict[str, str]] = {}
    for item in as_list(raw.get("objects")):
        if not isinstance(item, dict):
            continue
        object_id = str(item.get("object_id", item.get("id", "")) or "").strip()
        if not object_id:
            continue
        objects_by_id[object_id] = {
            "object_id": object_id,
            "description": str(item.get("description", object_id) or object_id).strip(),
            "category": str(item.get("category", "other") or "other").strip(),
        }
    for item in action_sequence:
        for key in ("object", "target"):
            object_id = item.get(key)
            if object_id and object_id not in objects_by_id:
                objects_by_id[str(object_id)] = {
                    "object_id": str(object_id),
                    "description": str(object_id),
                    "category": "other",
                }
    return {"robot_type": robot_type, "arms": arms, "objects": list(objects_by_id.values())}


def _timestamp_value(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def normalize_timestamped_action_sequence(
    value: Any,
    fallback_actions: list[dict[str, Any]],
    robot_type: str,
) -> list[dict[str, Any]]:
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
                "event_id": str(raw_dict.get("event_id") or fallback.get("event_id", f"E{index + 1:03d}")),
                "executor": executor,
                "action": action,
                "object": obj or None,
                "target": str(raw_dict.get("target") or fallback.get("target") or "").strip() or None,
                "start_time": _timestamp_value(raw_dict, "start_time", "startTime", "starttime"),
                "end_time": _timestamp_value(raw_dict, "end_time", "endTime", "endtime"),
            }
        )
    return normalized


def primitive_from_action(action: Any) -> str:
    text = str(action or "").strip().lower()
    return ACTION_TO_PRIMITIVE.get(text, ACTION_TO_PRIMITIVE.get(str(action or "").strip(), "idle"))


def normalize_phase_segments(
    value: Any,
    timestamped_actions: list[dict[str, Any]],
    robot_type: str,
    *,
    is_single_view: bool,
    fallback_actions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    raw_items = as_list(value)
    fallback = not raw_items
    fallback_from_actions = fallback and not timestamped_actions
    source_items = raw_items or timestamped_actions or (fallback_actions or [])
    phases: list[dict[str, Any]] = []
    for index, raw in enumerate(source_items, start=1):
        item = raw if isinstance(raw, dict) else {}
        action = str(item.get("action") or "").strip()
        primitive = str(item.get("primitive") or primitive_from_action(action)).strip().lower()
        if primitive not in PHASE_PRIMITIVES:
            primitive = "idle"
        flags = [str(flag) for flag in as_list(item.get("quality_flags")) if str(flag).strip()]
        if fallback and "fallback_from_timestampedActionSequence" not in flags:
            flags.append("fallback_from_action_sequence" if fallback_from_actions else "fallback_from_timestampedActionSequence")
        if is_single_view and "single_view" not in flags:
            flags.append("single_view")
        confidence = item.get("confidence", 0.6)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.6
        start_time = _timestamp_value(item, "start_time", "startTime", "starttime")
        end_time = _timestamp_value(item, "end_time", "endTime", "endtime")
        if (fallback or not start_time or not end_time) and "need_review" not in flags:
            flags.append("need_review")
        if is_single_view and confidence < 0.7 and "single_view_low_confidence" not in flags:
            flags.append("single_view_low_confidence")
        phases.append(
            {
                "phase_id": str(item.get("phase_id") or f"P{index:03d}"),
                "source_event_id": str(item.get("source_event_id") or item.get("event_id") or f"E{index:03d}"),
                "executor": normalize_executor(item.get("executor"), robot_type),
                "primitive": primitive,
                "action": action,
                "object": str(item.get("object") or "").strip() or None,
                "target": str(item.get("target") or "").strip() or None,
                "start_time": start_time,
                "end_time": end_time,
                "start_condition": str(item.get("start_condition", "") or "").strip(),
                "end_condition": str(item.get("end_condition", "") or "").strip(),
                "confidence": confidence,
                "quality_flags": flags,
            }
        )
    return phases


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
    if input_mode == "merged_views" and len(views) > 1:
        if language == "cn":
            rows = "\n".join(f"- 第 {i + 1} 行：{view}" for i, view in enumerate(views))
            return (
                "每一张输入图片都是同一时间点的多视角帧纵向拼接图。"
                "拼接前，每个视角图像会先按当前阶段配置的 resize_width 单独缩放；"
                "拼接后从上到下的行顺序如下：\n"
                f"{rows}\n"
                "第 1 行/第一个视角是主视角；描述 left/right/front/back/far/close 等空间方向时，"
                "必须以主视角为准，其他视角只用于补充确认遮挡、接触和深度关系。"
                "分析动作时请综合所有行的视角信息，不要把不同行误认为时间先后。"
                "动作的前后顺序以动作开始时间为准：哪个动作先开始，哪个动作就排在前面。"
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
    logger.debug(
        "Stage %s start images=%s max_tokens=%s temperature=%s top_p=%s top_k=%s",
        name,
        len(parts),
        max_tokens,
        temperature,
        top_p,
        top_k,
    )
    start = time.perf_counter()
    try:
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
        logger.info("Stage %s elapsed=%.2fs success=%s", name, time.perf_counter() - start, stage.success)
        logger.debug(
            "Stage %s token_usage prompt=%s completion=%s total=%s",
            name,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            usage.get("total_tokens", 0),
        )
        return stage
    except Exception:
        logger.exception("Stage %s failed elapsed=%.2fs", name, time.perf_counter() - start)
        raise
