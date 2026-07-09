"""JSON-oriented model call helpers."""

from __future__ import annotations

from typing import Any

from ..utils.api_client import call_vlm, extract_json_from_response


def call_json(
    client: Any,
    *,
    media_parts: list[dict[str, Any]],
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 0,
    temperature: float = 0.0,
    top_p: float = 0.95,
    top_k: int = 0,
) -> tuple[str, dict[str, int]]:
    return call_vlm(
        client,
        media_parts,
        system_prompt,
        user_prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
    )


def extract_json(raw_response: str) -> dict[str, Any] | None:
    return extract_json_from_response(raw_response)
