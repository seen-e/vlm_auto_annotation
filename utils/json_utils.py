"""JSON response utilities."""

from __future__ import annotations

from typing import Any

from .api_client import extract_json_from_response


def parse_json_response(text: str) -> tuple[dict[str, Any], list[str]]:
    parsed = extract_json_from_response(text)
    if isinstance(parsed, dict):
        return parsed, []
    return {}, ["No JSON object could be parsed from model response."]
