"""OpenAI-compatible VLM client helpers."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from .config import DEFAULT_BASE_URL, DEFAULT_MODEL


def create_openai_client(api_key: str | None = None, base_url: str | None = None):
    """Create an OpenAI-compatible client."""
    from openai import OpenAI

    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key, base_url=base_url or DEFAULT_BASE_URL)


def _is_qwen_model(model: str) -> bool:
    m = model.lower()
    return "qwen" in m or "qvq" in m


def _message_content(parts: list[dict[str, Any]], user_prompt: str, system_prompt: str) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    content.extend(parts)
    text = f"{system_prompt.strip()}\n\n{user_prompt.strip()}" if system_prompt else user_prompt.strip()
    content.append({"type": "text", "text": text})
    return content


def call_vlm(
    client,
    parts: list[dict[str, Any]],
    system_prompt: str,
    user_prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_retries: int = 3,
    temperature: float = 0.0,
    top_p: float = 0.95,
) -> tuple[str, dict[str, int]]:
    """Call a VLM and return (text, token_usage)."""
    if _is_qwen_model(model):
        messages = [{"role": "user", "content": _message_content(parts, user_prompt, system_prompt)}]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [*parts, {"type": "text", "text": user_prompt}]},
        ]

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
            )
            msg = response.choices[0].message
            content = msg.content.strip() if isinstance(msg.content, str) else ""
            usage_obj = getattr(response, "usage", None)
            usage = {
                "prompt_tokens": getattr(usage_obj, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(usage_obj, "completion_tokens", 0) or 0,
                "total_tokens": getattr(usage_obj, "total_tokens", 0) or 0,
            }
            return content, usage
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            last_error = exc
            time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"VLM call failed after {max_retries} attempts: {last_error}")


def _find_first_json_object(text: str) -> str | None:
    depth = 0
    start = None
    in_string = False
    escape_next = False

    for i, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if char == "\\" and in_string:
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start is not None:
                return text[start : i + 1]
    return None


def extract_json_from_response(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object from a model response."""
    text = text.strip()
    if not text:
        return None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()

    for block in re.findall(r"```(?:json|JSON)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL):
        try:
            return json.loads(block.strip())
        except json.JSONDecodeError:
            obj = _find_first_json_object(block)
            if obj:
                try:
                    return json.loads(obj)
                except json.JSONDecodeError:
                    pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        obj = _find_first_json_object(text)
        if obj:
            try:
                return json.loads(obj)
            except json.JSONDecodeError:
                return None
    return None
