"""Analysis parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from ...contracts.analysis import AnalysisStageOutput


@dataclass
class ParseResult:
    output: Any
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_analysis(raw_json: dict[str, Any] | None, context: Any, media_meta: dict[str, Any]) -> ParseResult:
    data = raw_json or {}
    try:
        output = AnalysisStageOutput(**data)
        return ParseResult(output=output)
    except (ValidationError, TypeError, ValueError) as exc:
        return ParseResult(output=AnalysisStageOutput(), errors=[str(exc)[:160]])
