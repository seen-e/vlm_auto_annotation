"""Adapters from legacy VLM outputs to normalized stage contracts."""

from __future__ import annotations

from typing import Any

from ..schemas import (
    AnalysisStageOutput,
    ExecutorInfo,
    ObjectInfo,
    RefinedSegment,
    RefinementStageOutput,
    SceneStageOutput,
    SegmentCandidate,
    SegmentChange,
)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text(value: Any, limit: int = 80) -> str:
    return str(value or "").strip()[:limit]


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def old_scene_output_to_new(raw: dict[str, Any] | None, meta: dict[str, Any] | None = None) -> SceneStageOutput:
    """Accept new scene_context or old sceneContext/arms/task_objects formats."""
    data = raw or {}
    context = data.get("scene_context") or data.get("sceneContext") or data
    if not isinstance(context, dict):
        context = {}

    selected_views = [str(view) for view in (meta or {}).get("selected_views", [])]
    primary_view = _text(context.get("primary_view") or (selected_views[0] if selected_views else ""))

    executors: list[ExecutorInfo] = []
    executor_object_map: dict[str, list[str]] = {}
    best_views: dict[str, list[str]] = {}

    raw_executors = context.get("executors")
    if raw_executors is None:
        raw_executors = context.get("arms")
    for item in _as_list(raw_executors):
        if not isinstance(item, dict):
            continue
        executor_id = _text(item.get("executor_id") or item.get("arm_id") or item.get("executor"))
        if not executor_id:
            continue
        views: list[str] = []
        for view in _as_list(item.get("best_observation_views")):
            name = _text(view.get("view_name")) if isinstance(view, dict) else _text(view)
            if name:
                views.append(name)
        handled = [_text(obj) for obj in _as_list(item.get("handled_objects")) if _text(obj)]
        executors.append(
            ExecutorInfo(
                executor_id=executor_id,
                description=_text(item.get("description")),
                main_workspace=_text(item.get("main_workspace")) or None,
                best_observation_views=views,
            )
        )
        if handled:
            executor_object_map[executor_id] = handled
        if views:
            best_views[executor_id] = views

    explicit_best = context.get("best_observation_views")
    if isinstance(explicit_best, dict):
        for key, value in explicit_best.items():
            views = [_text(item) for item in _as_list(value) if _text(item)]
            if views:
                best_views[_text(key)] = views

    def objects_from(primary_key: str, fallback_key: str | None = None) -> list[ObjectInfo]:
        raw_items = context.get(primary_key)
        if raw_items is None and fallback_key:
            raw_items = context.get(fallback_key)
        objects: list[ObjectInfo] = []
        for item in _as_list(raw_items):
            if not isinstance(item, dict):
                continue
            object_id = _text(item.get("object_id") or item.get("id"))
            if not object_id:
                continue
            objects.append(
                ObjectInfo(
                    object_id=object_id,
                    description=_text(item.get("description") or object_id),
                    role=_text(item.get("role") or ("background" if primary_key == "background_objects" else "")),
                )
            )
        return objects

    return SceneStageOutput(
        primary_view=primary_view or None,
        executors=executors,
        touched_objects=objects_from("touched_objects", "task_objects"),
        background_objects=objects_from("background_objects"),
        executor_object_map=executor_object_map,
        best_observation_views=best_views,
        scene_summary=_text(context.get("scene_summary") or context.get("main_action_summary"), 200),
    )


def old_analysis_output_to_new(raw: dict[str, Any] | None) -> AnalysisStageOutput:
    """Accept new candidate_segments or legacy action_sequence."""
    data = raw or {}
    raw_segments = data.get("candidate_segments")
    if raw_segments is None:
        raw_segments = data.get("action_sequence") or data.get("actionSequence") or []

    segments: list[SegmentCandidate] = []
    for index, item in enumerate(_as_list(raw_segments), start=1):
        if not isinstance(item, dict):
            continue
        action = _text(item.get("action"))
        if not action:
            continue
        objects = item.get("objects")
        if objects is None:
            obj = _text(item.get("object") or item.get("object_id"))
            objects = [obj] if obj else []
        segments.append(
            SegmentCandidate(
                segment_id=_text(item.get("segment_id") or item.get("event_id") or f"S{index:03d}"),
                start_time=_text(item.get("start_time")) or None,
                end_time=_text(item.get("end_time")) or None,
                start_frame=_int_or_none(item.get("start_frame")),
                end_frame=_int_or_none(item.get("end_frame")),
                executor=_text(item.get("executor") or item.get("arm") or "unknown"),
                action=action,
                objects=[_text(obj) for obj in _as_list(objects) if _text(obj)],
                evidence=_text(item.get("evidence"), 80),
                confidence=float(item.get("confidence") or 0.6),
            )
        )

    return AnalysisStageOutput(
        candidate_segments=segments,
        uncertain_regions=_as_list(data.get("uncertain_regions")),
        analysis_notes=data.get("analysis_notes") or [],
    )


def old_refinement_output_to_new(
    raw: dict[str, Any] | None,
    fallback: AnalysisStageOutput | None = None,
) -> RefinementStageOutput:
    """Accept refined_segments or legacy timestamped_action_sequence."""
    data = raw or {}
    raw_segments = data.get("refined_segments")
    if raw_segments is None:
        raw_segments = data.get("timestamped_action_sequence") or data.get("timestampedActionSequence") or []

    fallback_segments = fallback.candidate_segments if fallback else []
    segments: list[RefinedSegment] = []
    for index, item in enumerate(_as_list(raw_segments), start=1):
        if not isinstance(item, dict):
            continue
        base = fallback_segments[index - 1] if index - 1 < len(fallback_segments) else None
        action = _text(item.get("action") or (base.action if base else ""))
        if not action:
            continue
        objects = item.get("objects")
        if objects is None:
            obj = _text(item.get("object") or item.get("object_id") or ((base.objects[0] if base and base.objects else "")))
            objects = [obj] if obj else []
        segments.append(
            RefinedSegment(
                segment_id=_text(item.get("segment_id") or item.get("event_id") or (base.segment_id if base else f"S{index:03d}")),
                start_time=_text(item.get("start_time") or (base.start_time if base else "")) or None,
                end_time=_text(item.get("end_time") or (base.end_time if base else "")) or None,
                start_frame=_int_or_none(item.get("start_frame")) if item.get("start_frame") is not None else (base.start_frame if base else None),
                end_frame=_int_or_none(item.get("end_frame")) if item.get("end_frame") is not None else (base.end_frame if base else None),
                executor=_text(item.get("executor") or item.get("arm") or (base.executor if base else "unknown")),
                action=action,
                objects=[_text(obj) for obj in _as_list(objects) if _text(obj)],
                boundary_reason=_text(item.get("boundary_reason") or item.get("evidence")),
                confidence=float(item.get("confidence") or (base.confidence if base else 0.6)),
            )
        )

    changes: list[SegmentChange] = []
    for item in _as_list(data.get("changes")):
        if not isinstance(item, dict):
            continue
        changes.append(
            SegmentChange(
                original_segment_id=_text(item.get("original_segment_id") or item.get("segment_id")),
                change_type=str(item.get("change_type") or "keep").lower(),
                reason=_text(item.get("reason"), 30),
            )
        )
    if not changes:
        changes = [SegmentChange(original_segment_id=item.segment_id, change_type="keep", reason="") for item in segments]

    return RefinementStageOutput(refined_segments=segments, changes=changes)
