"""Stage parsers and compact validators."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from ..adapters import old_analysis_output_to_new, old_refinement_output_to_new, old_scene_output_to_new
from ..schemas import AnalysisStageOutput, RefinementStageOutput, SceneStageOutput, timestamp_to_seconds


@dataclass
class ParseResult:
    output: Any
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _msg(video_id: str | None, stage_name: str, message: str) -> str:
    return f"video_id={video_id or 'unknown'} stage={stage_name}: {message}"


def _valid_executors(scene: SceneStageOutput) -> set[str]:
    ids = {item.executor_id for item in scene.executors if item.executor_id}
    ids.update({"both", "unknown"})
    return ids


def _valid_objects(scene: SceneStageOutput) -> set[str]:
    return {item.object_id for item in [*scene.touched_objects, *scene.background_objects] if item.object_id}


def parse_scene_output(
    raw: dict[str, Any] | None,
    *,
    meta: dict[str, Any] | None = None,
    video_id: str | None = None,
) -> ParseResult:
    try:
        output = old_scene_output_to_new(raw, meta=meta)
        warnings: list[str] = []
        if not output.executors:
            warnings.append(_msg(video_id, "scene", "no executors"))
        if not output.primary_view:
            warnings.append(_msg(video_id, "scene", "missing primary_view"))
        return ParseResult(output=output, warnings=warnings)
    except (ValidationError, TypeError, ValueError) as exc:
        return ParseResult(output=SceneStageOutput(), errors=[_msg(video_id, "scene", str(exc)[:160])])


def parse_analysis_output(
    raw: dict[str, Any] | None,
    *,
    scene: SceneStageOutput,
    video_id: str | None = None,
) -> ParseResult:
    try:
        output = old_analysis_output_to_new(raw)
        warnings: list[str] = []
        executors = _valid_executors(scene)
        objects = _valid_objects(scene)
        for segment in output.candidate_segments:
            if executors and segment.executor not in executors:
                warnings.append(_msg(video_id, "analysis", f"executor '{segment.executor}' not in scene"))
            for obj in segment.objects:
                if objects and obj not in objects:
                    warnings.append(_msg(video_id, "analysis", f"object '{obj}' not in scene"))
        return ParseResult(output=output, warnings=warnings)
    except (ValidationError, TypeError, ValueError) as exc:
        return ParseResult(output=AnalysisStageOutput(), errors=[_msg(video_id, "analysis", str(exc)[:160])])


def parse_refinement_output(
    raw: dict[str, Any] | None,
    *,
    analysis: AnalysisStageOutput,
    scene: SceneStageOutput,
    video_id: str | None = None,
) -> ParseResult:
    try:
        output = old_refinement_output_to_new(raw, fallback=analysis)
        warnings: list[str] = []
        executors = _valid_executors(scene)
        objects = _valid_objects(scene)
        for segment in output.refined_segments:
            if executors and segment.executor not in executors:
                warnings.append(_msg(video_id, "refinement", f"executor '{segment.executor}' not in scene"))
            for obj in segment.objects:
                if objects and obj not in objects:
                    warnings.append(_msg(video_id, "refinement", f"object '{obj}' not in scene"))
            start = timestamp_to_seconds(segment.start_time)
            end = timestamp_to_seconds(segment.end_time)
            if start is not None and end is not None and start > end:
                segment.start_time, segment.end_time = segment.end_time, segment.start_time
                warnings.append(_msg(video_id, "refinement", f"swapped invalid boundary for {segment.segment_id}"))
        return ParseResult(output=output, warnings=warnings)
    except (ValidationError, TypeError, ValueError) as exc:
        return ParseResult(output=RefinementStageOutput(), errors=[_msg(video_id, "refinement", str(exc)[:160])])
