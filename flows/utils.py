"""Small helpers shared by named annotation flows."""

from __future__ import annotations

from importlib import import_module
import json
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
    return make_stage(name, raw, usage, fallback=fallback)
