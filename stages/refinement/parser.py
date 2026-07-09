"""Refinement parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from ...contracts.common import timestamp_to_seconds
from ...contracts.refinement import RefinementStageOutput


@dataclass
class ParseResult:
    output: Any
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_refinement(raw_json: dict[str, Any] | None, context: Any, media_meta: dict[str, Any]) -> ParseResult:
    data = raw_json or {}
    try:
        output = RefinementStageOutput(**data)
        warnings: list[str] = []
        for segment in output.refined_segments:
            start = timestamp_to_seconds(segment.start_time)
            end = timestamp_to_seconds(segment.end_time)
            if start is not None and end is not None and start > end:
                warnings.append(
                    f"video_id={context.video_id or 'unknown'} stage=refinement: invalid boundary for {segment.segment_id}"
                )
        return ParseResult(output=output, warnings=warnings)
    except (ValidationError, TypeError, ValueError) as exc:
        return ParseResult(output=RefinementStageOutput(), errors=[str(exc)[:160]])
