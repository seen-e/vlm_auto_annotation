"""Small helpers shared by named annotation flows."""

from __future__ import annotations

import json
from typing import Any

from ..utils.api_client import call_vlm, extract_json_from_response
from ..utils.config import DEFAULT_MODEL
from ..utils.schemas import StageResult


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def as_str_list(value: Any) -> list[str]:
    return [str(item).strip() for item in as_list(value) if str(item).strip()]


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
    temperature: float = 0.0,
) -> StageResult:
    raw, usage = call_vlm(
        client,
        parts,
        system_prompt,
        user_prompt,
        model=model,
        temperature=temperature,
    )
    return make_stage(name, raw, usage, fallback=fallback)
